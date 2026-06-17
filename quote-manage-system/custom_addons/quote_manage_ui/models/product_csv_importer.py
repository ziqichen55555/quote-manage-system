# -*- coding: utf-8 -*-
"""CSV inventory import with Series merge → Configuration variants (shop dropdown)."""
from __future__ import annotations

import base64
import csv
import io
import logging
import re
from collections import defaultdict

import requests
from markupsafe import escape

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CONFIG_ATTR_XMLID = "quote_manage_ui.attr_configuration"


class ProductCsvImporter(models.AbstractModel):
    _name = "product.csv.importer"
    _description = "Re-Ware CSV product import (Series merge)"

    # ------------------------------------------------------------------ API
    @api.model
    def import_from_path(self, path):
        with open(path, encoding="utf-8") as handle:
            return self.import_from_text(handle.read(), filename=path)

    @api.model
    def import_from_text(self, text, filename=None):
        if not (text or "").strip():
            raise UserError(_("The file is empty."))
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise UserError(_("Could not read CSV column headers."))
        required = {"section", "default_code", "title_raw", "cost_ex"}
        missing = required - {h.strip() for h in reader.fieldnames if h}
        if missing:
            raise UserError(
                _("Missing CSV columns: %s") % ", ".join(sorted(missing))
            )
        rows = list(reader)
        return self._run_import(rows)

    @api.model
    def import_from_binary(self, data, filename=None):
        try:
            raw = base64.b64decode(data)
        except Exception as exc:
            raise UserError(_("Could not decode the uploaded file.")) from exc
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return self.import_from_text(raw.decode(encoding), filename=filename)
            except UnicodeDecodeError:
                continue
        raise UserError(_("Could not read the file encoding (use UTF-8 CSV)."))

    # -------------------------------------------------------------- pipeline
    @api.model
    def _run_import(self, rows):
        sections = self._section_maps()
        units = self._aggregate_rows(rows)
        by_series = defaultdict(list)
        singles = []

        for unit in units:
            if unit["service"]:
                singles.append(unit)
                continue
            series = unit.get("series_key")
            if series:
                by_series[series].append(unit)
            else:
                singles.append(unit)

        created = updated = merged_groups = archived = stock_batches = 0

        for series_name, group in sorted(by_series.items()):
            if len(group) >= 2:
                c, u, a, s = self._import_merged_series(series_name, group, sections)
                created += c
                updated += u
                archived += a
                stock_batches += s
                merged_groups += 1
            else:
                singles.extend(group)

        for unit in singles:
            c, u, s = self._import_single_unit(unit, sections)
            created += c
            updated += u
            stock_batches += s

        self.env.cr.commit()
        return {
            "created": created,
            "updated": updated,
            "merged_series": merged_groups,
            "archived_skus": archived,
            "stock_batches": stock_batches,
            "sku_count": len(units),
        }

    @api.model
    def _aggregate_rows(self, rows):
        agg = defaultdict(
            lambda: {
                "qty": 0,
                "cost_num": 0.0,
                "cost_w": 0.0,
                "titles": [],
                "brands": [],
                "sections": [],
                "conditions": [],
                "units": [],
                "notes": [],
            }
        )
        for r in rows:
            code = (r.get("default_code") or "").strip()
            if not code:
                continue
            a = agg[code]
            sec = (r.get("section") or "").strip()
            if sec:
                a["sections"].append(sec)
            q = self._int(r.get("quantity"))
            a["qty"] += q
            cost = self._float(r.get("cost_ex"))
            if cost is not None and q > 0:
                a["cost_num"] += cost * q
                a["cost_w"] += q
            elif cost is not None and q == 0:
                a["cost_num"] = cost
                a["cost_w"] = 1.0
            title = (r.get("title_raw") or "").strip()
            if title:
                a["titles"].append(title)
            brand = (r.get("brand") or "").strip()
            if brand:
                a["brands"].append(brand)
            for key, col in (
                ("conditions", "condition_note"),
                ("units", "unit_identifiers"),
                ("notes", "row_note"),
            ):
                val = (r.get(col) or "").strip()
                if val:
                    a[key].append(val)

        out = []
        for code, a in sorted(agg.items()):
            cost_avg = None
            if a["cost_w"] and a["cost_w"] > 0:
                cost_avg = a["cost_num"] / a["cost_w"]
            elif a["cost_num"]:
                cost_avg = a["cost_num"]
            titles = a["titles"] or [code]
            brand = a["brands"][-1] if a["brands"] else ""
            specs = self._parse_specs(brand, titles)
            out.append(
                {
                    "code": code,
                    "service": code.upper() == "CCIT0001",
                    "qty": a["qty"],
                    "price": cost_avg if cost_avg is not None else 0.0,
                    "titles": titles,
                    "brand": brand,
                    "sections": a["sections"],
                    "conditions": a["conditions"],
                    "unit_ids": a["units"],
                    "notes": a["notes"],
                    "series_key": specs.get("series"),
                    "specs": specs,
                    "config_label": self._build_config_label(specs, code),
                }
            )
        return out

    # -------------------------------------------------------- merged series
    @api.model
    def _import_merged_series(self, series_name, group, sections):
        created = updated = archived = stock_batches = 0
        PT = self.env["product.template"].sudo()
        series_code = self._series_default_code(series_name)
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)
        tmpl = self._find_merged_template(series_name, series_code, config_attr)

        sec_key = (group[0]["sections"][-1] if group[0]["sections"] else "accessories").lower()
        if sec_key not in sections:
            sec_key = "accessories"
        categ_id, public_cmds, tag_cmds, ptype = sections[sec_key]

        prices = [u["price"] for u in group]
        base_price = min(prices) if prices else 0.0

        labels = self._unique_config_labels(group)
        config_vals = self._get_or_create_config_values(config_attr, labels)
        label_to_unit = {u["_final_config_label"]: u for u in group}

        vals = {
            "name": series_name,
            "default_code": series_code,
            "categ_id": categ_id,
            "public_categ_ids": public_cmds,
            "product_tag_ids": [(5, 0, 0)],
            "type": ptype,
            "list_price": base_price,
            "standard_price": base_price,
            "website_published": True,
            "sale_ok": True,
            "allow_out_of_stock_order": False,
            "show_availability": True,
            "description_sale": series_name[:500],
            "taxes_id": [(6, 0, self._default_sale_tax_ids())],
        }
        desc_html = self._build_group_description(group)
        if desc_html:
            vals["description"] = desc_html

        if tmpl:
            tmpl.write(vals)
            updated += 1
        else:
            tmpl = PT.create(vals)
            created += 1

        self._set_configuration_line(tmpl, config_attr, config_vals)
        self._clear_managed_attribute_lines(tmpl)
        tmpl.invalidate_recordset()

        for variant in tmpl.product_variant_ids:
            ptavs = variant.product_template_attribute_value_ids
            if not ptavs:
                continue
            label = ptavs[0].product_attribute_value_id.name
            unit = label_to_unit.get(label)
            if not unit:
                continue
            variant.write({"default_code": unit["code"]})
            ptav = ptavs[0]
            ptav.price_extra = unit["price"] - base_price
            stock_batches += self._apply_stock(variant, unit)

        for unit in group:
            code = unit["code"]
            old = PT.search(
                [("default_code", "=", code), ("id", "!=", tmpl.id)], limit=1
            )
            if old and old.active:
                old.write({"active": False, "website_published": False, "sale_ok": False})
                archived += 1

        try:
            self._sync_product_images(tmpl, series_name)
        except Exception as exc:
            _logger.warning("Image sync failed for %s: %s", series_name, exc)

        return created, updated, archived, stock_batches

    @api.model
    def _import_single_unit(self, unit, sections):
        created = updated = stock_batches = 0
        code = unit["code"]
        sec_key = (unit["sections"][-1] if unit["sections"] else "accessories").lower()
        if sec_key not in sections:
            sec_key = "accessories"
        categ_id, public_cmds, tag_cmds, ptype = sections[sec_key]
        if unit["service"]:
            ptype = "service"
            categ_id = self.env.ref("quote_manage_ui.product_category_services").id
            public_cmds = [(6, 0, [self.env.ref("quote_manage_ui.public_cat_services").id])]
            tag_cmds = [(5, 0, 0)]

        titles = unit["titles"]
        name = self._clean_title(titles[0], code)
        brand = unit["brand"]
        desc_html = self._build_unit_description(unit)
        uids_raw = " ".join(unit["unit_ids"])
        has_sn = "|" in uids_raw or "/" in uids_raw
        tracking = "serial" if (ptype == "product" and has_sn) else "none"

        PT = self.env["product.template"].sudo()
        tmpl = PT.search([("default_code", "=", code)], limit=1)
        vals = {
            "name": name,
            "default_code": code,
            "categ_id": categ_id,
            "public_categ_ids": public_cmds,
            "product_tag_ids": [(5, 0, 0)] if ptype == "product" else tag_cmds,
            "type": ptype,
            "tracking": tracking,
            "list_price": unit["price"],
            "standard_price": unit["price"],
            "website_published": True,
            "sale_ok": True,
            "description_sale": (f"{brand} · {code}".strip(" ·") if brand else code)[:500],
            "allow_out_of_stock_order": ptype != "product",
            "show_availability": ptype == "product",
            "taxes_id": [(6, 0, self._default_sale_tax_ids())],
        }
        if desc_html:
            vals["description"] = desc_html
        if tmpl:
            tmpl.write(vals)
            updated += 1
        else:
            vals["barcode"] = code
            tmpl = PT.create(vals)
            created += 1

        series_name = self._sync_template_attributes(tmpl, brand=brand, titles=titles, ptype=ptype)
        if series_name and ptype == "product":
            tmpl.write({"name": series_name})

        try:
            self._sync_product_images(tmpl, tmpl.name)
        except Exception as exc:
            _logger.warning("Image sync failed for %s: %s", tmpl.name, exc)

        if ptype == "product" and unit["qty"] > 0 and len(tmpl.product_variant_ids) == 1:
            stock_batches += self._apply_stock(tmpl.product_variant_id, unit)

        return created, updated, stock_batches

    # ------------------------------------------------------------- helpers
    @api.model
    def _default_sale_tax_ids(self):
        tax = self.env.company.account_sale_tax_id
        return tax.ids if tax else []

    @api.model
    def _find_merged_template(self, series_name, series_code, config_attr):
        PT = self.env["product.template"].sudo()
        tmpl = PT.search([("default_code", "=", series_code)], limit=1)
        if not tmpl:
            tmpl = PT.search(
                [
                    ("name", "=", series_name),
                    ("attribute_line_ids.attribute_id", "=", config_attr.id),
                ],
                limit=1,
            )
        return tmpl

    @api.model
    def _series_default_code(self, series_name):
        slug = re.sub(r"[^A-Z0-9]+", "-", (series_name or "").upper()).strip("-")
        return f"RW-SERIES-{slug}"[:80]

    @api.model
    def _unique_config_labels(self, group):
        seen = {}
        labels = []
        for unit in group:
            lbl = unit["config_label"]
            if lbl in seen:
                seen[lbl] += 1
                lbl = f"{lbl} ({unit['code']})"
            else:
                seen[lbl] = 1
            labels.append(lbl)
            unit["_final_config_label"] = lbl
        return labels

    @api.model
    def _build_config_label(self, specs, code):
        parts = []
        if specs.get("cpu"):
            parts.append(specs["cpu"])
        if specs.get("ram"):
            parts.append(specs["ram"])
        if specs.get("storage"):
            parts.append(specs["storage"])
        if specs.get("touch"):
            parts.append("Touch")
        if specs.get("wan"):
            parts.append("WAN")
        return " / ".join(parts) if parts else code

    @api.model
    def _get_or_create_config_values(self, attribute, labels):
        PAV = self.env["product.attribute.value"].sudo()
        out = []
        for label in labels:
            name = (label or "")[:128]
            found = PAV.search(
                [("attribute_id", "=", attribute.id), ("name", "=", name)], limit=1
            )
            out.append(found or PAV.create({"attribute_id": attribute.id, "name": name}))
        return out

    @api.model
    def _set_configuration_line(self, tmpl, config_attr, config_vals):
        Line = self.env["product.template.attribute.line"].sudo()
        Line.search([("product_tmpl_id", "=", tmpl.id)]).unlink()
        Line.create(
            {
                "product_tmpl_id": tmpl.id,
                "attribute_id": config_attr.id,
                "value_ids": [(6, 0, [v.id for v in config_vals])],
            }
        )

    @api.model
    def _clear_managed_attribute_lines(self, tmpl):
        managed = [
            self.env.ref(x).id
            for x in (
                "quote_manage_ui.attr_brand",
                "quote_manage_ui.attr_series",
                "quote_manage_ui.attr_cpu",
                "quote_manage_ui.attr_ram",
                "quote_manage_ui.attr_storage",
                "quote_manage_ui.attr_touchscreen",
                "quote_manage_ui.attr_wan",
            )
        ]
        self.env["product.template.attribute.line"].sudo().search(
            [("product_tmpl_id", "=", tmpl.id), ("attribute_id", "in", managed)]
        ).unlink()

    @api.model
    def _apply_stock(self, variant, unit):
        if "stock.quant" not in self.env or unit["qty"] <= 0:
            return 0
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if not wh:
            return 0
        tmpl = variant.product_tmpl_id
        tracking = tmpl.tracking
        uids_raw = " ".join(unit["unit_ids"])
        has_sn = "|" in uids_raw or "/" in uids_raw
        if has_sn and tracking != "serial":
            tmpl.tracking = "serial"
            tracking = "serial"

        if tracking == "serial":
            units = []
            for u_str in unit["unit_ids"]:
                units.extend(
                    [x.strip() for x in u_str.replace("|", "/").split("/") if x.strip()]
                )
            for i in range(int(unit["qty"])):
                lot_name = units[i] if i < len(units) else f"S/N-{unit['code']}-{i+1:03d}"
                lot = self.env["stock.lot"].sudo().search(
                    [
                        ("product_id", "=", variant.id),
                        ("name", "=", lot_name),
                        ("company_id", "=", self.env.company.id),
                    ],
                    limit=1,
                )
                if not lot:
                    lot = self.env["stock.lot"].sudo().create(
                        {
                            "product_id": variant.id,
                            "name": lot_name,
                            "company_id": self.env.company.id,
                        }
                    )
                sq = self.env["stock.quant"].sudo().search(
                    [
                        ("product_id", "=", variant.id),
                        ("location_id", "=", wh.lot_stock_id.id),
                        ("lot_id", "=", lot.id),
                    ],
                    limit=1,
                )
                if sq:
                    sq.with_context(inventory_mode=True).write(
                        {"inventory_quantity_auto_apply": 1.0}
                    )
                else:
                    self.env["stock.quant"].sudo().with_context(
                        inventory_mode=True
                    ).create(
                        {
                            "product_id": variant.id,
                            "location_id": wh.lot_stock_id.id,
                            "lot_id": lot.id,
                            "inventory_quantity_auto_apply": 1.0,
                        }
                    )
        else:
            sq = self.env["stock.quant"].sudo().search(
                [
                    ("product_id", "=", variant.id),
                    ("location_id", "=", wh.lot_stock_id.id),
                    ("lot_id", "=", False),
                ],
                limit=1,
            )
            target = float(unit["qty"])
            if sq:
                sq.with_context(inventory_mode=True).write(
                    {"inventory_quantity_auto_apply": target}
                )
            else:
                self.env["stock.quant"].sudo().with_context(inventory_mode=True).create(
                    {
                        "product_id": variant.id,
                        "location_id": wh.lot_stock_id.id,
                        "inventory_quantity_auto_apply": target,
                    }
                )
        return 1

    @api.model
    def _build_group_description(self, group):
        parts = ["<p><strong>Available configurations</strong></p><ul>"]
        for u in group:
            parts.append(
                f"<li>{escape(u.get('_final_config_label', u['config_label']))}: "
                f"${u['price']:.0f} ({escape(u['code'])})</li>"
            )
        parts.append("</ul>")
        return "".join(parts)

    @api.model
    def _build_unit_description(self, unit):
        parts = []
        if len(unit["titles"]) > 1:
            parts.append("<p><strong>Alternate titles</strong></p><ul>")
            for t in unit["titles"][1:]:
                parts.append(f"<li>{escape(t)}</li>")
            parts.append("</ul>")
        if unit["conditions"]:
            parts.append(
                "<p><strong>Condition</strong>: "
                + escape(", ".join(unit["conditions"]))
                + "</p>"
            )
        if unit["unit_ids"]:
            parts.append(
                "<p><strong>Unit IDs</strong>: "
                + escape(" | ".join(unit["unit_ids"]))
                + "</p>"
            )
        return "".join(parts) if parts else False

    @api.model
    def _float(self, val):
        if val is None or str(val).strip() == "":
            return None
        try:
            return float(str(val).strip())
        except ValueError:
            return None

    @api.model
    def _int(self, val):
        if val is None or str(val).strip() == "":
            return 0
        try:
            return int(float(str(val).strip()))
        except ValueError:
            return 0

    @api.model
    def _section_maps(self):
        def ref(xmlid):
            return self.env.ref(xmlid).id

        return {
            "laptops": (
                ref("quote_manage_ui.product_category_computer_systems_refurb"),
                [
                    (
                        6,
                        0,
                        [
                            ref("quote_manage_ui.public_cat_laptops"),
                            ref("quote_manage_ui.public_cat_laptops_computer_systems"),
                        ],
                    )
                ],
                [(6, 0, [ref("quote_manage_ui.product_tag_computer_systems")])],
                "product",
            ),
            "docks": (
                ref("quote_manage_ui.product_category_docks"),
                [(6, 0, [ref("quote_manage_ui.public_cat_docks")])],
                [(6, 0, [ref("quote_manage_ui.product_tag_docks")])],
                "product",
            ),
            "desktops": (
                ref("quote_manage_ui.product_category_workstations"),
                [(6, 0, [ref("quote_manage_ui.public_cat_desktops")])],
                [(6, 0, [ref("quote_manage_ui.product_tag_desktops")])],
                "product",
            ),
            "accessories": (
                ref("quote_manage_ui.product_category_pc_accessories"),
                [(6, 0, [ref("quote_manage_ui.public_cat_accessories")])],
                [(6, 0, [ref("quote_manage_ui.product_tag_accessories")])],
                "product",
            ),
            "monitors": (
                ref("quote_manage_ui.product_category_monitors"),
                [(6, 0, [ref("quote_manage_ui.public_cat_monitors")])],
                [(6, 0, [ref("quote_manage_ui.product_tag_monitors")])],
                "product",
            ),
            "networking": (
                ref("quote_manage_ui.product_category_pc_accessories"),
                [(6, 0, [ref("quote_manage_ui.public_cat_accessories")])],
                [(6, 0, [ref("quote_manage_ui.product_tag_accessories")])],
                "product",
            ),
        }

    # ------------------------------------------ title / attribute parsing
    @api.model
    def _clean_title(self, title, code):
        t = (title or "").strip()
        for p in (
            "Re-Ware ",
            "Re-ware ",
            "Re-WareLenovo",
            "Re-WareLenovo ",
            "Co-Creative IT & ",
        ):
            if t.upper().startswith(p.upper()):
                t = t[len(p) :].strip()
        t = re.split(r"[,(\[]", t)[0].strip()
        t = re.sub(
            r"\s+(i[3579]|CPU|@|Intel|\d+\s?GB|\d+\s?SSD|USB-C|USB-A|DOCK|DOCKING|SFF|Tiny|Mini|Switch|cloud-managed|Layer\s?2|port|Gigabit|Ethernet|PoE\+|SFP).*$",
            "",
            t,
            flags=re.I,
        ).strip()
        t = re.sub(r"^Odell", "Dell", t, flags=re.I)
        if "THINKPAD" in t.upper():
            t = re.sub(r"(ThinkPad\s+[A-Z0-9]+).*$", r"\1", t, flags=re.I).strip()
            if not t.startswith("Lenovo"):
                t = f"Lenovo {t}"
        if "LATITUDE" in t.upper() or "OPTIPLEX" in t.upper():
            t = re.sub(
                r"((?:Latitude|Optiplex)\s+[A-Z0-9]+).*$", r"\1", t, flags=re.I
            ).strip()
            if not t.startswith("Dell"):
                t = f"Dell {t}"
        return (t[:200] if t else code) or code

    @api.model
    def _parse_specs(self, brand, titles):
        blob = " ".join(titles).strip()
        blob = re.sub(r"\b4\s*G\s*LTE\b", "", blob, flags=re.I)
        t_up = blob.upper()
        specs = {}

        if brand:
            specs["brand"] = brand
        elif "DELL" in t_up:
            specs["brand"] = "Dell"
        elif "LENOVO" in t_up or "THINKPAD" in t_up:
            specs["brand"] = "Lenovo"

        if "T490" in t_up or "T490S" in t_up:
            specs["series"] = "ThinkPad T490s"
        elif "T14S" in t_up or ("T14" in t_up and "T490" not in t_up):
            specs["series"] = "ThinkPad T14s"
        elif "T15" in t_up:
            specs["series"] = "ThinkPad T15"
        elif "P1" in t_up and ("GEN 3" in t_up or "GEN3" in t_up.replace(" ", "")):
            specs["series"] = "ThinkPad P1"
        elif "T480" in t_up:
            specs["series"] = "ThinkPad T480s"
        elif "LAT3301" in t_up:
            specs["series"] = "Latitude 3301"
        elif "LAT5590" in t_up or "LAT5591" in t_up:
            specs["series"] = "Dell 5590"
        elif "LATITUDE" in t_up:
            m = re.search(r"Latitude\s+([A-Z0-9]+)", blob, re.I)
            specs["series"] = f"Dell {m.group(1) if m else 'Latitude'}"
        elif "OPTIPLEX" in t_up:
            m = re.search(r"Optiplex\s+([A-Z0-9]+)", blob, re.I)
            specs["series"] = f"Optiplex {m.group(1) if m else 'Optiplex'}"
        elif "TOUGHBOOK" in t_up or "FZ55" in t_up or "CF-54" in t_up or "CF 54" in t_up:
            specs["series"] = "Toughbook"
        elif "M910" in t_up or "SFF" in t_up:
            specs["series"] = "Lenovo"

        if re.search(r"I5[-\s]?10210U|102IOU", t_up):
            specs["cpu"] = "i5-10210U"
        elif "1135G7" in t_up or "1145G7" in t_up:
            specs["cpu"] = "11th Gen i5/i7"
        elif "7300U" in t_up:
            specs["cpu"] = "i5-7300U"
        elif "8365U" in t_up:
            specs["cpu"] = "i5-8365U"
        elif "10885" in t_up or "I9" in t_up:
            specs["cpu"] = "i9"

        ram_m = re.search(r"(\d+)\s*G[B]?\s*RAM", blob, re.I)
        if ram_m:
            specs["ram"] = f"{int(ram_m.group(1))}GB"
        else:
            all_gb = re.findall(r"(\d+)\s*G[B]?", blob, re.I)
            if len(all_gb) >= 2:
                gb = int(all_gb[-1])
                if gb <= 64:
                    specs["ram"] = f"{gb}GB"
            elif len(all_gb) == 1 and int(all_gb[0]) <= 64:
                specs["ram"] = f"{int(all_gb[0])}GB"

        if re.search(r"1\s*TB\s*SSD", blob, re.I):
            specs["storage"] = "1TB SSD"
        else:
            st_m = re.search(r"(\d+)\s*(?:GB|G)\s*SSD", blob, re.I)
            if st_m:
                specs["storage"] = f"{st_m.group(1)}GB SSD"
            else:
                nums = [int(x) for x in re.findall(r"(\d+)\s*G[B]?", blob, re.I)]
                big = [x for x in nums if x > 64]
                if big:
                    specs["storage"] = f"{max(big)}GB SSD"
                elif "500GB" in t_up:
                    specs["storage"] = "500GB"

        if "TOUCH" in t_up:
            specs["touch"] = "Yes"
        if "WAN" in t_up or " LTE" in t_up:
            specs["wan"] = "Yes"

        return specs

    @api.model
    def _sync_template_attributes(self, tmpl, *, brand, titles, ptype):
        """Legacy single-SKU attribute lines for shop filters."""
        if ptype != "product":
            return None
        specs = self._parse_specs(brand, titles)
        Line = self.env["product.template.attribute.line"].sudo()
        managed = [
            self.env.ref(x).id
            for x in (
                "quote_manage_ui.attr_brand",
                "quote_manage_ui.attr_series",
                "quote_manage_ui.attr_cpu",
                "quote_manage_ui.attr_ram",
                "quote_manage_ui.attr_storage",
                "quote_manage_ui.attr_touchscreen",
                "quote_manage_ui.attr_wan",
            )
        ]
        Line.search(
            [("product_tmpl_id", "=", tmpl.id), ("attribute_id", "in", managed)]
        ).unlink()

        def add_line(attr_xml, value_name):
            if not value_name:
                return
            attr = self.env.ref(attr_xml)
            val = self.env["product.attribute.value"].sudo().search(
                [("attribute_id", "=", attr.id), ("name", "=ilike", value_name)],
                limit=1,
            )
            if not val:
                val = self.env["product.attribute.value"].sudo().create(
                    {"attribute_id": attr.id, "name": value_name[:128]}
                )
            Line.create(
                {
                    "product_tmpl_id": tmpl.id,
                    "attribute_id": attr.id,
                    "value_ids": [(6, 0, [val.id])],
                }
            )

        if specs.get("brand"):
            add_line("quote_manage_ui.attr_brand", specs["brand"])
        if specs.get("series"):
            add_line("quote_manage_ui.attr_series", specs["series"])
        if specs.get("cpu"):
            add_line("quote_manage_ui.attr_cpu", specs["cpu"])
        if specs.get("ram"):
            add_line("quote_manage_ui.attr_ram", specs["ram"])
        if specs.get("storage"):
            add_line("quote_manage_ui.attr_storage", specs["storage"])
        if specs.get("touch"):
            add_line("quote_manage_ui.attr_touchscreen", "Yes")
        if specs.get("wan"):
            add_line("quote_manage_ui.attr_wan", "Enabled")
        return specs.get("series")

    @api.model
    def _sync_product_images(self, tmpl, title):
        """Optional demo images — skipped when requests unavailable."""
        return
