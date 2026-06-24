# -*- coding: utf-8 -*-
"""CSV inventory import — one shop product per MTM/SKU (name + model)."""
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
# Refurb computers imported via CSV — always serial-tracked.
SERIAL_TRACK_SECTIONS = frozenset({"laptops", "desktops"})


class ProductCsvImporter(models.AbstractModel):
    _name = "product.csv.importer"
    _description = "Re-Ware CSV product import (additive — new SKUs + stock only)"

    # ------------------------------------------------------------------ API
    @api.model
    def import_from_path(self, path):
        with open(path, encoding="utf-8-sig") as handle:
            return self.import_from_text(handle.read(), filename=path)

    @api.model
    def import_from_text(self, text, filename=None):
        text = (text or "").lstrip("\ufeff")
        if not text.strip():
            raise UserError(_("The file is empty."))
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise UserError(_("Could not read CSV column headers."))
        headers = {h.strip() for h in reader.fieldnames if h}
        rows = list(reader)
        if self._is_merged_device_export(headers):
            rows = self._merged_device_rows_to_import_rows(rows)
            return self._run_import(rows, additive=True)
        else:
            required = {"section", "default_code", "title_raw", "cost_ex"}
            missing = required - headers
            if missing:
                raise UserError(
                    _("Missing CSV columns: %s") % ", ".join(sorted(missing))
                )
        return self._run_import(rows, additive=True)

    @api.model
    def _is_merged_device_export(self, headers):
        """re-ware merge output: one row per device (Serial + MTM from Blancco join)."""
        norm = {h.strip().lower() for h in headers}
        return "serial" in norm and "mtm" in norm

    @api.model
    def _merged_str(self, row, *keys, default=""):
        for key in keys:
            for k, v in row.items():
                if k and k.strip().lower() == key.lower():
                    if v is None:
                        continue
                    s = str(v).strip()
                    if s:
                        return s
        return default

    @api.model
    def _merged_int_gb(self, val):
        s = (val or "").strip()
        if not s:
            return "0"
        if re.search(r"\d{4}G\d", s, re.I):
            return "0"
        m = re.search(r"(\d+)", s)
        if not m:
            return "0"
        n = int(m.group(1))
        if n in self._cpu_model_storage_false_positives(s):
            return "0"
        return str(n)

    @api.model
    def _cpu_model_storage_false_positives(self, text):
        """Digits from CPU strings like i5-1135G7 — must not be treated as SSD GB."""
        blob = text or ""
        false = {int(x) for x in re.findall(r"i[3579]-(\d{4})G\d", blob, re.I)}
        false.update({int(x) for x in re.findall(r"\b(\d{4})G\d\b", blob, re.I)})
        return false

    @api.model
    def _merged_section(self, model_name, mtm):
        name = (model_name or "").lower()
        desktop_kw = (
            "thinkcentre", "thinkstation", "optiplex", "prodesk",
            "elitedesk", "tiny", " sff", "desktop", "workstation",
            "m70", "m73", "m910", "m920", "m93",
        )
        if any(k in name for k in desktop_kw):
            return "Desktops"
        if any(k in name for k in (
            "thinkpad", "latitude", "toughbook", "elitebook", "laptop", "panasonic",
        )):
            return "Laptops"
        if (mtm or "").startswith("20") and len(mtm) == 10:
            return "Laptops"
        return "Laptops"

    @api.model
    def _merged_brand(self, manufacturer):
        m = (manufacturer or "").strip().upper()
        return {
            "LENOVO": "Lenovo",
            "DELL": "Dell",
            "HP": "HP",
            "PANASONIC": "Panasonic",
        }.get(m, manufacturer or "Lenovo")

    @api.model
    def _merged_title(self, row):
        brand = self._merged_brand(self._merged_str(row, "Manufacturer"))
        model = self._merged_str(row, "Model name")
        parts = [f"Re-Ware {brand}"]
        if model:
            parts.append(model)
        cpu = self._merged_str(row, "CPU")
        if cpu:
            parts.append(cpu)
        ssd = self._merged_int_gb(self._merged_str(row, "SSD size (GB)", "SSD size"))
        if ssd != "0":
            parts.append(f"{ssd}GB SSD")
        ram = self._merged_int_gb(self._merged_str(row, "RAM (GB)", "RAM"))
        if ram != "0":
            parts.append(f"{ram}GB RAM")
        if self._merged_str(row, "Touch").lower() == "yes":
            parts.append("TOUCHSCREEN")
        if self._merged_str(row, "WAN").lower() == "yes":
            parts.append("WAN ENABLED")
        gen = self._merged_str(row, "Generation")
        if gen:
            parts.append(f"Gen {gen}")
        return ", ".join(parts)

    @api.model
    def _shop_model_subtitle(self, code, product_name=""):
        """Sales description on shop = MTM / model code, not the product title."""
        code = (code or "").strip()
        name = (product_name or "").strip()
        if code and code != name and not code.startswith("RW-SERIES-"):
            return code
        return code or name

    @api.model
    def _merged_series_model_subtitle(self, group):
        codes = sorted({u["code"] for u in group if u.get("code")})
        codes = [c for c in codes if c and not c.startswith("RW-SERIES-")]
        if len(codes) == 1:
            return codes[0]
        if codes:
            return ", ".join(codes[:6])
        return group[0]["code"] if group else ""

    @api.model
    def fix_shop_model_subtitles(self):
        """Set description_sale to MTM when it duplicates the product name."""
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        fixed = 0
        for tmpl in PT.search([("sale_ok", "=", True), ("website_published", "=", True)]):
            label = tmpl._rw_shop_model_label()
            if not label:
                continue
            desc = (tmpl.description_sale or "").strip()
            if desc == label:
                continue
            if desc == (tmpl.name or "").strip() or not desc or desc.lower().startswith("imported sheet"):
                tmpl.description_sale = label[:500]
                fixed += 1
        return fixed

    @api.model
    def _is_valid_series_name(self, series):
        s = (series or "").strip()
        if len(s) < 8:
            return False
        if re.fullmatch(r"[A-Z0-9]{1,4}", s, re.I):
            return False
        low = s.lower()
        if "kbc" in low or "version" in low:
            return False
        markers = (
            "thinkpad", "thinkcentre", "latitude", "optiplex", "toughbook",
            "dell", "lenovo", "panasonic", "elitebook",
        )
        return any(m in low for m in markers)

    @api.model
    def _canonical_series_name(self, series):
        s = (series or "").strip()
        s = re.sub(r"\bThinkpad\b", "ThinkPad", s, flags=re.I)
        s = re.sub(r"\bThinkcentre\b", "ThinkCentre", s, flags=re.I)
        if re.search(r"T490", s, re.I):
            return "ThinkPad T490s"
        m = re.search(r"T14s?\s*Gen\s*(\d+\w*)", s, re.I)
        if m:
            return f"ThinkPad T14s Gen {m.group(1)}"
        m = re.search(r"T15\s*Gen\s*(\d+\w*)", s, re.I)
        if m:
            return f"ThinkPad T15 Gen {m.group(1)}"
        m = re.search(r"P1\s*Gen\s*(\d+\w*)", s, re.I)
        if m:
            return f"ThinkPad P1 Gen {m.group(1)}"
        if re.search(r"T480", s, re.I):
            return "ThinkPad T480s"
        if re.search(r"T14S", s, re.I):
            return "ThinkPad T14s"
        if re.search(r"M910", s, re.I):
            return "ThinkCentre M910s"
        if re.search(r"M70Q", s, re.I):
            return "ThinkCentre M70q"
        return s

    @api.model
    def _normalize_product_name(self, name):
        s = (name or "").strip()
        s = re.sub(r"\bThinkpad\b", "ThinkPad", s, flags=re.I)
        s = re.sub(r"\bThinkcentre\b", "ThinkCentre", s, flags=re.I)
        return s

    @api.model
    def _is_valid_product_name(self, name):
        return self._is_valid_series_name(name)

    @api.model
    def _resolve_product_key(
        self,
        system_version="",
        series="",
        brand="",
        model_name="",
        mtm="",
        generation="",
        titles=None,
    ):
        """Shop product = Blancco System version (e.g. ThinkPad T14s Gen 2i ≠ Gen 1)."""
        sv = (system_version or "").strip()
        if self._is_valid_product_name(sv):
            return self._normalize_product_name(sv)
        if self._is_valid_product_name(series):
            return self._normalize_product_name(series)
        return self._resolve_series_key(
            series=series,
            brand=brand,
            model_name=model_name,
            mtm=mtm,
            generation=generation,
            titles=titles,
        )

    @api.model
    def _short_cpu_label(self, cpu_raw):
        s = (cpu_raw or "").strip()
        if not s:
            return ""
        m = re.search(r"\bi[3579]-[\w]+", s, re.I)
        if m:
            return m.group(0)
        m = re.search(r"(\d{4}G\d)", s, re.I)
        if m:
            prefix = "i5" if "i5" in s.lower() else "i7" if "i7" in s.lower() else "CPU"
            return f"{prefix}-{m.group(1)}"
        return s[:64]

    @api.model
    def _merged_specs_from_fields(self, brand, mtm, cpu_raw, ram_gb, ssd_gb, touch, wan):
        specs = {"brand": brand, "mtm": (mtm or "").upper()}
        cpu = self._short_cpu_label(cpu_raw)
        if cpu:
            specs["cpu"] = cpu
        ram = self._merged_int_gb(ram_gb)
        if ram != "0":
            specs["ram"] = f"{ram}GB"
        ssd = self._merged_int_gb(ssd_gb)
        if ssd != "0":
            specs["storage"] = f"{ssd}GB SSD"
        if (touch or "").strip().lower() == "yes":
            specs["touch"] = "Yes"
        if (wan or "").strip().lower() == "yes":
            specs["wan"] = "Yes"
        return specs

    @api.model
    def _resolve_series_key(
        self, series="", brand="", model_name="", mtm="", generation="", titles=None
    ):
        if self._is_valid_series_name(series):
            return self._canonical_series_name(series)
        gen = (generation or "").strip()
        model_u = (model_name or "").upper()
        mtm_u = (mtm or "").upper()
        if "T490" in model_u or mtm_u in ("20NYS4CP00", "20NYS4CP01"):
            return "ThinkPad T490s"
        if any(x in model_u for x in ("T14S", "T14 ")) or mtm_u.startswith(
            ("20T", "20WN", "20WNS")
        ):
            if gen:
                return f"ThinkPad T14s Gen {gen}"
        if "T15" in model_u or mtm_u.startswith("20W4"):
            if gen:
                return f"ThinkPad T15 Gen {gen}"
            return "ThinkPad T15"
        if "T480" in model_u or mtm_u.startswith("20L8"):
            return "ThinkPad T480s"
        if "M910" in model_u or mtm_u.startswith("10ML"):
            return "ThinkCentre M910s"
        if titles:
            specs = self._parse_specs(brand, titles)
            if specs.get("series"):
                return self._canonical_series_name(specs["series"])
        return ""

    @api.model
    def _merged_group_key(self, row):
        return (
            self._merged_str(row, "MTM").upper(),
            self._merged_str(row, "Generation"),
            self._merged_str(row, "Model name"),
            self._merged_int_gb(self._merged_str(row, "RAM (GB)", "RAM")),
            self._merged_int_gb(self._merged_str(row, "SSD size (GB)", "SSD size")),
            self._merged_str(row, "Touch"),
            self._merged_str(row, "WAN"),
            self._merged_str(row, "CPU"),
        )

    @api.model
    def _merged_sku_code(self, mtm, model_name, ram, ssd, touch):
        ram_i = self._merged_int_gb(ram)
        ssd_i = self._merged_int_gb(ssd)
        touch_flag = "T" if (touch or "").strip().lower() == "yes" else "N"
        return f"{mtm}-{ram_i}G-{ssd_i}G-{touch_flag}"

    @api.model
    def _merged_device_rows_to_import_rows(self, rows):
        """Convert re-ware merge CSV (per device) → inventory import rows (per SKU)."""
        ok = [
            r for r in rows
            if self._merged_str(r, "Status", default="SUCCESS").upper() == "SUCCESS"
            and self._merged_str(r, "Serial")
        ]
        if not ok:
            raise UserError(
                _("No SUCCESS rows with serial numbers found in the merge export.")
            )

        by_mtm_configs = defaultdict(set)
        for row in ok:
            mtm = self._merged_str(row, "MTM").upper()
            gen = self._merged_str(row, "Generation")
            by_mtm_configs[(mtm, gen)].add(self._merged_group_key(row))

        buckets = defaultdict(list)
        for row in ok:
            buckets[self._merged_group_key(row)].append(row)

        out = []
        for key in sorted(buckets.keys()):
            group = buckets[key]
            sample = group[0]
            mtm = self._merged_str(sample, "MTM").upper()
            gen = self._merged_str(sample, "Generation")
            model_name = self._merged_str(sample, "Model name")
            if len(by_mtm_configs.get((mtm, gen), set())) == 1:
                code = mtm
            else:
                code = self._merged_sku_code(
                    mtm,
                    model_name,
                    self._merged_str(sample, "RAM (GB)", "RAM"),
                    self._merged_str(sample, "SSD size (GB)", "SSD size"),
                    self._merged_str(sample, "Touch"),
                )
            serials = sorted({
                self._merged_str(r, "Serial").upper()
                for r in group
                if self._merged_str(r, "Serial")
            })
            price = self._merged_str(sample, "Price")
            brand = self._merged_brand(self._merged_str(sample, "Manufacturer"))
            title = self._merged_title(sample)
            system_version = self._merged_str(sample, "System version")
            product_key = self._resolve_product_key(
                system_version=system_version,
                series=self._merged_str(sample, "Series"),
                brand=brand,
                model_name=model_name,
                mtm=mtm,
                generation=gen,
                titles=[title],
            )
            if product_key and product_key.lower() not in title.lower():
                title = f"Re-Ware {product_key}, {title.replace('Re-Ware ', '', 1)}"
            out.append({
                "section": self._merged_section(model_name, mtm),
                "default_code": code,
                "title_raw": title,
                "brand": brand,
                "series": product_key,
                "product_key": product_key,
                "system_version": system_version,
                "mtm_code": mtm,
                "cpu_raw": self._merged_str(sample, "CPU"),
                "ram_gb": self._merged_str(sample, "RAM (GB)", "RAM"),
                "ssd_gb": self._merged_str(sample, "SSD size (GB)", "SSD size"),
                "touch_val": self._merged_str(sample, "Touch"),
                "wan_val": self._merged_str(sample, "WAN"),
                "quantity": str(len(serials)),
                "cost_ex": price,
                "condition_note": self._merged_str(sample, "Mobo status"),
                "unit_identifiers": "|".join(serials),
                "row_note": "merged_blancco",
            })
        return out

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
    def _run_import(self, rows, additive=False):
        sections = self._section_maps()
        units = self._aggregate_rows(rows)

        # Additive import: only SKUs present in the CSV are touched. No archiving,
        # no overwriting existing products, no zeroing stock for absent SKUs.
        created = updated = stock_batches = skipped_serials = 0

        for unit in units:
            c, u, s, sk = self._import_single_unit(unit, sections, additive=additive)
            created += c
            updated += u
            stock_batches += s
            skipped_serials += sk

        self.env.cr.commit()
        return {
            "created": created,
            "updated": updated,
            "merged_series": 0,
            "archived_skus": 0,
            "stock_batches": stock_batches,
            "skipped_serials": skipped_serials,
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
                "series_keys": [],
                "product_keys": [],
                "merged_fields": [],
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
            series = (r.get("series") or r.get("product_key") or "").strip()
            if series:
                a["series_keys"].append(series)
            product_key = (r.get("product_key") or r.get("system_version") or series).strip()
            if product_key:
                a["product_keys"].append(product_key)
            if (r.get("row_note") or "").strip() == "merged_blancco":
                a["merged_fields"].append({
                    "brand": (r.get("brand") or "").strip(),
                    "mtm": (r.get("mtm_code") or "").strip(),
                    "cpu_raw": (r.get("cpu_raw") or "").strip(),
                    "ram_gb": (r.get("ram_gb") or "").strip(),
                    "ssd_gb": (r.get("ssd_gb") or "").strip(),
                    "touch": (r.get("touch_val") or "").strip(),
                    "wan": (r.get("wan_val") or "").strip(),
                })
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
            if a["merged_fields"]:
                mf = a["merged_fields"][-1]
                specs = self._merged_specs_from_fields(
                    mf["brand"] or brand,
                    mf["mtm"] or code,
                    mf["cpu_raw"],
                    mf["ram_gb"],
                    mf["ssd_gb"],
                    mf["touch"],
                    mf["wan"],
                )
            else:
                specs = self._parse_specs(brand, titles)
            series_key = ""
            if a["product_keys"]:
                series_key = self._normalize_product_name(a["product_keys"][0])
            elif a["series_keys"]:
                series_key = self._normalize_product_name(a["series_keys"][0])
            if not series_key:
                series_key = specs.get("series")
            if series_key:
                specs["series"] = series_key
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
                    "series_key": series_key,
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

        sec_key = (group[0]["sections"][-1] if group[0].get("sections") else "accessories").lower()
        if sec_key not in sections:
            sec_key = "accessories"
        categ_id, public_cmds, tag_cmds, ptype = sections[sec_key]

        # When merging existing DB products, keep their categories from source rows.
        source_ids = [u["_source_tmpl_id"] for u in group if u.get("_source_tmpl_id")]
        if source_ids:
            sources = PT.browse(source_ids).exists()
            if sources:
                categ_id = sources[0].categ_id.id
                public_ids = list(set(sources.mapped("public_categ_ids").ids))
                public_cmds = [(6, 0, public_ids)] if public_ids else [(5, 0, 0)]
                ptype = sources[0].type or "product"

        prices = [u["price"] for u in group if u.get("price", 0) > 0]
        base_price = min(prices) if prices else 0.0

        labels = self._unique_config_labels(group)
        config_vals = self._get_or_create_config_values(config_attr, labels)
        label_to_unit = {u["_final_config_label"]: u for u in group}

        all_unit_ids = [uid for u in group for uid in u.get("unit_ids", [])]
        vals = {
            "name": series_name,
            "default_code": series_code,
            "categ_id": categ_id,
            "public_categ_ids": public_cmds,
            "product_tag_ids": [(5, 0, 0)],
            "type": ptype,
            "tracking": self._resolve_tracking(
                ptype, sec_key, all_unit_ids, categ_id=categ_id
            ),
            "website_published": True,
            "sale_ok": True,
            "allow_out_of_stock_order": False,
            "show_availability": True,
            "description_sale": self._merged_series_model_subtitle(group)[:500],
            "taxes_id": [(6, 0, self._default_sale_tax_ids())],
        }
        desc_html = self._build_group_description(group)
        if desc_html:
            vals["description"] = desc_html

        if base_price > 0:
            vals["list_price"] = base_price
            vals["standard_price"] = base_price
        elif tmpl:
            vals["list_price"] = tmpl.list_price
            vals["standard_price"] = tmpl.standard_price

        if tmpl:
            tmpl.write(vals)
            updated += 1
        else:
            tmpl = PT.create(vals)
            created += 1

        effective_base = base_price if base_price > 0 else (tmpl.list_price or 0.0)

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
            if unit.get("price", 0) > 0:
                ptav.price_extra = unit["price"] - effective_base
            if unit.get("_source_tmpl_id"):
                old_tmpl = PT.browse(unit["_source_tmpl_id"])
                if (
                    old_tmpl.exists()
                    and old_tmpl.id != tmpl.id
                    and old_tmpl.product_variant_count == 1
                ):
                    stock_batches += self._migrate_variant_stock(
                        old_tmpl.product_variant_id, variant
                    )
            else:
                applied, _skipped = self._apply_stock(variant, unit)
                stock_batches += applied

        source_tmps = PT.browse(
            [u["_source_tmpl_id"] for u in group if u.get("_source_tmpl_id")]
        ).exists()
        if source_tmps:
            self._preserve_images(tmpl, source_tmps)

        for unit in group:
            code = unit["code"]
            old = PT.browse(unit["_source_tmpl_id"]) if unit.get("_source_tmpl_id") else PT.browse()
            if not old:
                old = PT.search(
                    [("default_code", "=", code), ("id", "!=", tmpl.id)], limit=1
                )
            if old and old.id != tmpl.id and old.active:
                old.write({"active": False, "website_published": False, "sale_ok": False})
                archived += 1

        try:
            if not source_tmps:
                self._sync_product_images(tmpl, series_name)
        except Exception as exc:
            _logger.warning("Image sync failed for %s: %s", series_name, exc)

        return created, updated, archived, stock_batches

    @api.model
    def _ensure_published(self, tmpl):
        """Restore shop visibility only — never change name, price, or attributes."""
        updates = {}
        if not tmpl.active:
            updates["active"] = True
        if not tmpl.website_published:
            updates["website_published"] = True
        if not tmpl.sale_ok:
            updates["sale_ok"] = True
        if updates:
            tmpl.write(updates)

    @api.model
    def _is_merged_unit(self, unit):
        if "merged_blancco" in (unit.get("notes") or []):
            return True
        return bool((unit.get("specs") or {}).get("mtm"))

    @api.model
    def _refresh_existing_from_merge_unit(
        self, tmpl, unit, code, brand, titles, ptype, config_attr
    ):
        """Re-apply Blancco-backed name + filter attributes on additive merge upload."""
        specs = unit.get("specs") or {}
        shop_name = unit.get("series_key") or specs.get("series") or tmpl.name
        updates = {}
        if shop_name and shop_name != tmpl.name:
            updates["name"] = shop_name
        subtitle = self._shop_model_subtitle(code, shop_name)[:500]
        if subtitle and subtitle != (tmpl.description_sale or "").strip():
            updates["description_sale"] = subtitle
        if updates:
            tmpl.write(updates)
        if ptype != "product" or not specs:
            return
        tmpl.attribute_line_ids.filtered(
            lambda l: l.attribute_id.id == config_attr.id
        ).unlink()
        self._sync_template_attributes(
            tmpl,
            brand=brand or specs.get("brand", ""),
            titles=titles,
            ptype=ptype,
            specs=specs,
        )

    @api.model
    def _ensure_active_variant(self, tmpl, code):
        """Reactivate a variant when a per-MTM template was archived without its variant."""
        variants = tmpl.product_variant_ids.with_context(active_test=False)
        active = variants.filtered(lambda v: v.active)
        if active:
            return active[:1]
        match = variants.filtered(lambda v: (v.default_code or "").strip() == code)
        to_activate = match or (variants if len(variants) == 1 else variants[:1])
        if to_activate:
            to_activate.write({"active": True, "sale_ok": True})
        return to_activate[:1]

    @api.model
    def _stock_variant_for_unit(self, tmpl, code):
        variants = tmpl.product_variant_ids.filtered(lambda v: v.active)
        if not variants:
            variants = self._ensure_active_variant(tmpl, code)
        if not variants:
            return self.env["product.product"]
        if len(variants) == 1:
            return variants[0]
        match = variants.filtered(lambda v: (v.default_code or "").strip() == code)
        return match[:1] or variants[:1]

    @api.model
    def _import_single_unit(self, unit, sections, additive=False):
        created = updated = stock_batches = skipped_serials = 0
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
        product_name = unit.get("series_key") or self._clean_title(titles[0], code)
        brand = unit["brand"]
        desc_html = self._build_unit_description(unit)
        tracking = self._resolve_tracking(
            ptype, sec_key, unit["unit_ids"], categ_id=categ_id
        )

        PT = self.env["product.template"].sudo().with_context(active_test=False)
        tmpl = PT.search([("default_code", "=", code)], limit=1)
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)

        if tmpl and additive:
            self._ensure_published(tmpl)
            self._ensure_active_variant(tmpl, code)
            if self._is_merged_unit(unit):
                self._refresh_existing_from_merge_unit(
                    tmpl, unit, code, brand, titles, ptype, config_attr
                )
                updated += 1
            variant = self._stock_variant_for_unit(tmpl, code)
            if ptype == "product" and unit["qty"] > 0 and variant:
                applied, skipped = self._apply_stock(
                    variant, unit, additive=True
                )
                stock_batches += applied
                skipped_serials += skipped
            return created, updated, stock_batches, skipped_serials

        price = unit["price"] if unit.get("price", 0) > 0 else 0.0
        vals = {
            "name": product_name,
            "default_code": code,
            "categ_id": categ_id,
            "public_categ_ids": public_cmds,
            "product_tag_ids": [(5, 0, 0)] if ptype == "product" else tag_cmds,
            "type": ptype,
            "tracking": tracking,
            "website_published": True,
            "sale_ok": True,
            "active": True,
            "description_sale": self._shop_model_subtitle(code, product_name)[:500],
            "allow_out_of_stock_order": ptype != "product",
            "show_availability": ptype == "product",
            "taxes_id": [(6, 0, self._default_sale_tax_ids())],
        }
        if price > 0:
            vals["list_price"] = price
            vals["standard_price"] = price
        elif tmpl:
            vals["list_price"] = tmpl.list_price
            vals["standard_price"] = tmpl.standard_price
        else:
            vals["list_price"] = 0.0
            vals["standard_price"] = 0.0
        if desc_html:
            vals["description"] = desc_html
        if tmpl:
            tmpl.write(vals)
            updated += 1
        else:
            vals["barcode"] = code
            tmpl = PT.create(vals)
            created += 1

        if ptype == "product":
            tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == config_attr.id
            ).unlink()

        specs = unit.get("specs") or self._parse_specs(brand, titles)
        series_name = self._sync_template_attributes(
            tmpl, brand=brand, titles=titles, ptype=ptype, specs=specs
        )
        self._ensure_active_variant(tmpl, code)
        shop_name = unit.get("series_key") or series_name or product_name
        if shop_name and ptype == "product":
            tmpl.write({
                "name": shop_name,
                "description_sale": self._shop_model_subtitle(code, shop_name)[:500],
            })

        try:
            self._sync_product_images(tmpl, tmpl.name)
        except Exception as exc:
            _logger.warning("Image sync failed for %s: %s", tmpl.name, exc)

        variant = self._stock_variant_for_unit(tmpl, code)
        if ptype == "product" and unit["qty"] > 0 and variant:
            applied, skipped = self._apply_stock(
                variant, unit, additive=bool(created)
            )
            stock_batches += applied
            skipped_serials += skipped

        return created, updated, stock_batches, skipped_serials

    # ------------------------------------------------------------- helpers
    @api.model
    def _serial_tracking_categ_ids(self):
        return {
            self.env.ref("quote_manage_ui.product_category_computer_systems_refurb").id,
            self.env.ref("quote_manage_ui.product_category_workstations").id,
        }

    @api.model
    def _has_unit_serial(self, unit_ids):
        return bool("".join(unit_ids or []).strip())

    @api.model
    def _resolve_tracking(self, ptype, sec_key, unit_ids, categ_id=None):
        """Serial for refurb computers; accessories/docks only when CSV has unit IDs."""
        if ptype != "product":
            return "none"
        key = (sec_key or "").lower()
        if key in SERIAL_TRACK_SECTIONS:
            return "serial"
        if self._has_unit_serial(unit_ids):
            return "serial"
        if categ_id and categ_id in self._serial_tracking_categ_ids():
            return "serial"
        return "none"

    @api.model
    def fix_product_serial_tracking(self):
        """Repair laptop/desktop and merged-series products set to No Tracking."""
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)
        serial_categ_ids = self._serial_tracking_categ_ids()
        fixed = 0
        for tmpl in PT.search(
            [("type", "=", "product"), ("tracking", "!=", "serial"), ("active", "=", True)]
        ):
            if tmpl.categ_id.id in serial_categ_ids or self._is_configuration_only_product(
                tmpl, config_attr
            ):
                tmpl.tracking = "serial"
                fixed += 1
        return fixed

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
        if specs.get("mtm"):
            parts.append(specs["mtm"])
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
    def _apply_stock(self, variant, unit, additive=False):
        if "stock.quant" not in self.env or unit["qty"] <= 0:
            return 0, 0
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if not wh:
            return 0, 0
        tmpl = variant.product_tmpl_id
        sec_key = (unit["sections"][-1] if unit.get("sections") else "accessories").lower()
        want_serial = self._resolve_tracking(
            tmpl.type,
            sec_key,
            unit.get("unit_ids", []),
            categ_id=tmpl.categ_id.id,
        )
        tracking = tmpl.tracking
        if want_serial == "serial" and tracking != "serial":
            tmpl.tracking = "serial"
            tracking = "serial"

        applied = skipped = 0
        Lot = self.env["stock.lot"].sudo()
        if tracking == "serial":
            units = []
            for u_str in unit["unit_ids"]:
                units.extend(
                    [x.strip() for x in u_str.replace("|", "/").split("/") if x.strip()]
                )
            for i in range(int(unit["qty"])):
                lot_name = units[i] if i < len(units) else f"S/N-{unit['code']}-{i+1:03d}"
                if additive:
                    existing = Lot.search(
                        [("name", "=", lot_name), ("company_id", "=", self.env.company.id)],
                        limit=1,
                    )
                    if existing:
                        skipped += 1
                        continue
                lot = Lot.search(
                    [
                        ("product_id", "=", variant.id),
                        ("name", "=", lot_name),
                        ("company_id", "=", self.env.company.id),
                    ],
                    limit=1,
                )
                if not lot:
                    lot = Lot.create(
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
                if sq and sq.quantity > 0:
                    skipped += 1
                    continue
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
                applied += 1
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
            if additive:
                current = sq.quantity if sq else 0.0
                target = current + float(unit["qty"])
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
            applied = 1
        return applied, skipped

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
            gen_m = re.search(r"GEN\s*(\d+\w*)", t_up)
            if gen_m:
                specs["series"] = f"ThinkPad T14s Gen {gen_m.group(1)}"
        elif "T15" in t_up:
            specs["series"] = "ThinkPad T15"
            gen_m = re.search(r"GEN\s*(\d+\w*)", t_up)
            if gen_m:
                specs["series"] = f"ThinkPad T15 Gen {gen_m.group(1)}"
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
        elif re.search(r"M70Q|M70\s*Q", t_up) or "11T300A1AU" in t_up:
            specs["series"] = "ThinkCentre M70q"
        elif "M910" in t_up or "THINKCENTRE M910" in t_up or "10MLS" in t_up:
            specs["series"] = "ThinkCentre M910s"

        if re.search(r"I5[-\s]?10210U|102IOU", t_up):
            specs["cpu"] = "i5-10210U"
        elif re.search(r"I5[-\s]?6500|6500", t_up) and "I7" not in t_up:
            specs["cpu"] = "i5-6500"
        elif "1145G7" in t_up:
            specs["cpu"] = "i5-1145G7"
        elif "1135G7" in t_up:
            specs["cpu"] = "i5-1135G7"
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

        storage_blob = re.sub(
            r"11th\s+Gen[^,|]*|i[3579]-\d{4}G\d[^,|]*|@\s*[\d.]+\s*GHz",
            " ",
            blob,
            flags=re.I,
        )
        cpu_false_gb = self._cpu_model_storage_false_positives(blob)
        if re.search(r"1\s*TB\s*SSD", storage_blob, re.I):
            specs["storage"] = "1TB SSD"
        else:
            st_m = re.search(r"(\d+)\s*(?:GB|G)\s*SSD", storage_blob, re.I)
            if st_m and int(st_m.group(1)) not in cpu_false_gb:
                specs["storage"] = f"{st_m.group(1)}GB SSD"
            else:
                nums = [
                    int(x)
                    for x in re.findall(
                        r"(?<![\d])(\d{2,4})\s*G[B]?\b", storage_blob, re.I
                    )
                ]
                big = [
                    x
                    for x in nums
                    if 64 < x <= 2048 and x not in cpu_false_gb
                ]
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
    def repair_cpu_model_storage_attrs(self):
        """Fix Storage values mis-parsed from i5-1135G7 / i5-1145G7 CPU model numbers."""
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        storage_attr = self.env.ref("quote_manage_ui.attr_storage")
        bad_vals = self.env["product.attribute.value"].sudo().search([
            ("attribute_id", "=", storage_attr.id),
            "|",
            ("name", "ilike", "1135%"),
            ("name", "ilike", "1145%"),
        ])
        if not bad_vals:
            return 0
        bad_ids = set(bad_vals.ids)
        fixed = 0
        for tmpl in PT.search([("default_code", "!=", False)]):
            storage_lines = tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == storage_attr.id
                and set(l.value_ids.ids) & bad_ids
            )
            if not storage_lines:
                continue
            brand = ""
            for line in tmpl.attribute_line_ids:
                if line.attribute_id.name == "Brand" and line.value_ids:
                    brand = line.value_ids[0].name
                    break
            titles = [t for t in (tmpl.name, tmpl.description_sale) if t]
            specs = self._parse_specs(brand, titles)
            storage = (specs.get("storage") or "").lower()
            if not storage or "1135gb" in storage or "1145gb" in storage:
                blob = " ".join(titles).upper()
                if re.search(r"\b512\b", blob):
                    specs["storage"] = "512GB SSD"
                elif re.search(r"\b256\b", blob):
                    specs["storage"] = "256GB SSD"
            self._sync_template_attributes(
                tmpl,
                brand=brand,
                titles=titles,
                ptype=tmpl.type,
                specs=specs,
            )
            fixed += 1
        return fixed

    @api.model
    def fix_thinkcentre_m910_series(self):
        """Re-apply Series=ThinkCentre M910s on existing M910 SKU rows (pre-merge fix)."""
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)
        fixed = 0
        for tmpl in PT.search([("sale_ok", "=", True), ("type", "=", "product")]):
            if self._is_configuration_only_product(tmpl, config_attr):
                continue
            haystack = " ".join(
                x for x in (tmpl.name, tmpl.default_code, tmpl.description_sale) if x
            ).upper()
            if "M910" not in haystack and "10MLS" not in haystack:
                continue
            titles = [tmpl.description_sale or tmpl.name or tmpl.default_code or ""]
            self._sync_template_attributes(
                tmpl, brand="Lenovo", titles=titles, ptype="product"
            )
            fixed += 1
        return fixed

    @api.model
    def _sync_template_attributes(self, tmpl, *, brand, titles, ptype, specs=None):
        """Legacy single-SKU attribute lines for shop filters."""
        if ptype != "product":
            return None
        if not specs:
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

    # ------------------------------------------- merge existing DB products
    @api.model
    def _archive_configuration_parent_for_sku(self, code):
        """Archive a legacy Configuration parent when the SKU only exists as a variant."""
        code = (code or "").strip()
        if not code:
            return 0
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)
        PP = self.env["product.product"].sudo().with_context(active_test=False)
        archived = 0
        for variant in PP.search([("default_code", "=", code), ("active", "=", True)]):
            tmpl = variant.product_tmpl_id
            if not tmpl.active or tmpl.default_code == code:
                continue
            if not tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == config_attr.id
            ):
                continue
            tmpl.write({"active": False, "website_published": False, "sale_ok": False})
            archived += 1
        return archived

    @api.model
    def archive_configuration_dropdown_products(self):
        """Unpublish legacy shop listings that use a Configuration dropdown."""
        config_attr = self.env.ref(CONFIG_ATTR_XMLID)
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        candidates = PT.search([
            ("active", "=", True),
            ("attribute_line_ids.attribute_id", "=", config_attr.id),
        ])
        archived = 0
        for tmpl in candidates:
            tmpl.write({"active": False, "website_published": False, "sale_ok": False})
            archived += 1
        return archived

    @api.model
    def archive_series_configuration_products(self):
        """Backward-compatible alias for migrations."""
        return self.archive_configuration_dropdown_products()

    @api.model
    def merge_existing_catalog(self):
        """Archive legacy Configuration dropdown listings; re-upload CSV for separate SKUs."""
        archived = self.archive_configuration_dropdown_products()
        return {
            "merged_series": 0,
            "created": 0,
            "updated": 0,
            "archived_skus": archived,
            "stock_migrations": 0,
            "message": (
                "Archived %(archived)s old combined shop product(s) that used a "
                "Configuration dropdown (e.g. ThinkPad T490s with multiple MTM/SKU "
                "options on one page).\n\n"
                "Each MTM/SKU is now its own listing. Re-upload your MERGED CSV under "
                "Upload inventory CSV to recreate separate products and stock."
            ) % {"archived": archived},
        }

    @api.model
    def _is_configuration_only_product(self, tmpl, config_attr):
        lines = tmpl.attribute_line_ids
        if not lines:
            return False
        has_config = bool(lines.filtered(lambda l: l.attribute_id.id == config_attr.id))
        has_series = bool(
            lines.filtered(
                lambda l: l.attribute_id.id
                == self.env.ref("quote_manage_ui.attr_series").id
            )
        )
        return has_config and not has_series

    @api.model
    def _template_to_merge_unit(self, tmpl):
        specs = self._specs_from_template(tmpl)
        code = tmpl.default_code or f"TMPL-{tmpl.id}"
        return {
            "code": code,
            "service": False,
            "qty": max(int(tmpl.qty_available), 1) if tmpl.qty_available else 0,
            "price": tmpl.list_price,
            "titles": [tmpl.name or code],
            "brand": specs.get("brand", ""),
            "sections": [],
            "conditions": [],
            "unit_ids": [],
            "notes": [],
            "series_key": specs.get("series"),
            "specs": specs,
            "config_label": self._build_config_label(specs, code),
            "_source_tmpl_id": tmpl.id,
        }

    @api.model
    def _specs_from_template(self, tmpl):
        mapping = {
            "Brand": "brand",
            "Series": "series",
            "CPU": "cpu",
            "RAM": "ram",
            "Storage": "storage",
            "Touchscreen": "touch",
            "WAN": "wan",
        }
        specs = {}
        for line in tmpl.attribute_line_ids:
            key = mapping.get(line.attribute_id.name)
            if key and line.value_ids:
                specs[key] = line.value_ids[0].name
        if specs.get("touch") == "Yes":
            specs["touch"] = "Yes"
        if specs.get("wan") in ("Enabled", "Yes"):
            specs["wan"] = "Yes"
        return specs

    @api.model
    def _preserve_images(self, merged_tmpl, source_templates):
        """Copy main + gallery images from source products (lowest price wins main)."""
        sources = source_templates.filtered("image_1920").sorted("list_price")
        if sources and not merged_tmpl.image_1920:
            merged_tmpl.image_1920 = sources[0].image_1920
        elif sources:
            merged_tmpl.image_1920 = sources[0].image_1920

        Image = self.env["product.image"].sudo()
        seen = set(merged_tmpl.product_template_image_ids.mapped("name"))
        for src in source_templates:
            for img in src.product_template_image_ids:
                if img.name in seen:
                    continue
                Image.create(
                    {
                        "name": img.name,
                        "product_tmpl_id": merged_tmpl.id,
                        "image_1920": img.image_1920,
                    }
                )
                seen.add(img.name)

    @api.model
    def _migrate_variant_stock(self, old_variant, new_variant):
        """Move on-hand stock from old variant to new variant after a Series merge.

        Serial/lot rows cannot have ``product_id`` rewritten once stock moves
        exist (Odoo blocks it). Copy quantity onto the target variant via
        inventory adjustment and zero the source instead.
        """
        if not old_variant or not new_variant or old_variant.id == new_variant.id:
            return 0
        Quant = self.env["stock.quant"].sudo()
        Lot = self.env["stock.lot"].sudo()
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if not wh:
            return 0

        count = 0
        quants = Quant.search(
            [
                ("product_id", "=", old_variant.id),
                ("location_id", "child_of", wh.lot_stock_id.id),
                ("quantity", ">", 0),
            ]
        )
        for quant in quants:
            qty = quant.quantity
            if qty <= 0:
                continue
            location = quant.location_id
            if quant.lot_id:
                new_lot = Lot.search(
                    [
                        ("product_id", "=", new_variant.id),
                        ("name", "=", quant.lot_id.name),
                        ("company_id", "=", self.env.company.id),
                    ],
                    limit=1,
                )
                if not new_lot:
                    new_lot = Lot.create(
                        {
                            "product_id": new_variant.id,
                            "name": quant.lot_id.name,
                            "company_id": self.env.company.id,
                        }
                    )
                dest = Quant.search(
                    [
                        ("product_id", "=", new_variant.id),
                        ("location_id", "=", location.id),
                        ("lot_id", "=", new_lot.id),
                    ],
                    limit=1,
                )
                if dest:
                    dest.with_context(inventory_mode=True).write(
                        {"inventory_quantity_auto_apply": dest.quantity + qty}
                    )
                else:
                    Quant.with_context(inventory_mode=True).create(
                        {
                            "product_id": new_variant.id,
                            "location_id": location.id,
                            "lot_id": new_lot.id,
                            "inventory_quantity_auto_apply": qty,
                        }
                    )
            else:
                dest = Quant.search(
                    [
                        ("product_id", "=", new_variant.id),
                        ("location_id", "=", location.id),
                        ("lot_id", "=", False),
                    ],
                    limit=1,
                )
                if dest:
                    dest.with_context(inventory_mode=True).write(
                        {"inventory_quantity_auto_apply": dest.quantity + qty}
                    )
                else:
                    try:
                        quant.product_id = new_variant.id
                        count += 1
                        continue
                    except Exception:
                        Quant.with_context(inventory_mode=True).create(
                            {
                                "product_id": new_variant.id,
                                "location_id": location.id,
                                "inventory_quantity_auto_apply": qty,
                            }
                        )
            quant.with_context(inventory_mode=True).write(
                {"inventory_quantity_auto_apply": 0.0}
            )
            count += 1
        return count

    @api.model
    def _sync_product_images(self, tmpl, title):
        """Optional demo images — skipped when requests unavailable."""
        return
