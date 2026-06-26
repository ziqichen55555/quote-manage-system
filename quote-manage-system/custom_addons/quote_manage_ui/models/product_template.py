# -*- coding: utf-8 -*-
import base64
import logging
import re

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

IMAGE_URL_RE = re.compile(r'(https?://[^\s<>"\']+)')
IMAGE_EXT_RE = re.compile(r'\.(png|jpe?g|webp|gif)(\?.*)?$', re.IGNORECASE)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_quote_deduplicate_attribute_lines(self):
        """Remove duplicate *active* attribute lines with identical attribute + values.

        Duplicate rows on the same template cause the eCommerce "single value"
        table to repeat ``Brand: X, X, X...`` and clutter the backend form.
        """
        Line = self.env["product.template.attribute.line"]
        total_removed = 0
        for tmpl in self:
            lines = tmpl.attribute_line_ids.filtered(lambda l: l.active).sorted(
                lambda l: (l.sequence, l.id)
            )
            seen = {}
            to_unlink = Line.browse()
            for ptal in lines:
                key = (ptal.attribute_id.id, frozenset(ptal.value_ids.ids))
                if key in seen:
                    to_unlink |= ptal
                else:
                    seen[key] = ptal
            if to_unlink:
                to_unlink.unlink()
                total_removed += len(to_unlink)
        if not total_removed:
            raise UserError(
                _(
                    "No duplicate attribute lines were found. "
                    "Duplicates must share the same attribute and the same set of values."
                )
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Attributes deduplicated"),
                "message": _("Removed %(count)s duplicate line(s).", count=total_removed),
                "type": "success",
                "sticky": False,
            },
        }

    def _quote_extract_image_url_from_sale_description(self):
        """Extract first usable image URL from Sales Description."""
        self.ensure_one()
        text = self.description_sale or ""
        if not text:
            return False

        candidates = [m.group(1).strip() for m in IMAGE_URL_RE.finditer(text)]
        if not candidates:
            return False

        for url in candidates:
            if IMAGE_EXT_RE.search(url):
                return url
        return candidates[0]

    def _quote_fetch_and_set_image(self, url):
        """Download URL content and write to image_1920."""
        self.ensure_one()
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "image/" not in content_type:
            raise ValueError(f"URL is not an image: {url}")
        self.image_1920 = base64.b64encode(response.content)

    @api.model
    def action_quote_sync_images_from_sales_description(self, limit=200, overwrite=False):
        """Sync product image from URL stored in Sales Description.

        Put an image URL in the product Sales Description (description_sale),
        then call this method to import images in batch.
        """
        domain = [('description_sale', '!=', False)]
        products = self.search(domain, limit=limit)
        updated = 0
        skipped = 0
        errors = 0
        for product in products:
            if product.image_1920 and not overwrite:
                skipped += 1
                continue
            url = product._quote_extract_image_url_from_sale_description()
            if not url:
                skipped += 1
                continue
            try:
                product._quote_fetch_and_set_image(url)
                updated += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                _logger.warning(
                    "Image sync failed for %s (%s): %s",
                    product.default_code or product.id,
                    url,
                    exc,
                )
        return {"updated": updated, "skipped": skipped, "errors": errors}

    @api.model
    def quote_copy_product_images(self, source_code, target_codes, overwrite=True):
        """Copy main + gallery images from one SKU to others (same model photos)."""
        PT = self.sudo()
        src = PT.search([("default_code", "=ilike", (source_code or "").strip())], limit=1)
        if not src:
            return {"error": "source_not_found", "source": source_code}
        Image = self.env["product.image"].sudo()
        results = []
        for code in target_codes or []:
            code = (code or "").strip()
            if not code or code.upper() == (source_code or "").upper():
                continue
            tgt = PT.search([("default_code", "=ilike", code)], limit=1)
            if not tgt:
                results.append({"sku": code, "status": "not_found"})
                continue
            if overwrite:
                tgt.product_template_image_ids.unlink()
            if src.image_1920:
                tgt.image_1920 = src.image_1920
            for img in src.product_template_image_ids:
                if not img.image_1920:
                    continue
                Image.create(
                    {
                        "name": img.name,
                        "product_tmpl_id": tgt.id,
                        "image_1920": img.image_1920,
                    }
                )
            results.append({"sku": code, "status": "copied", "gallery": len(src.product_template_image_ids)})
        return {"source": src.default_code, "results": results}

    def _quote_image_donor_for(self):
        """Find a catalog product with photos for the same model (base MTM or name)."""
        self.ensure_one()
        PT = self.env["product.template"].sudo().with_context(active_test=False)
        code = (self.default_code or "").strip()
        base = self._rw_shop_display_code(code).upper()
        name = (self.name or "").strip()

        if base:
            exact = PT.search(
                [
                    ("id", "!=", self.id),
                    ("default_code", "=ilike", base),
                    ("image_1920", "!=", False),
                ],
                limit=1,
            )
            if exact:
                return exact
            for donor in PT.search([("id", "!=", self.id), ("image_1920", "!=", False)]):
                if self._rw_shop_display_code(donor.default_code or "").upper() == base:
                    return donor

        if name:
            by_name = PT.search(
                [
                    ("id", "!=", self.id),
                    ("name", "=", name),
                    ("image_1920", "!=", False),
                ],
                limit=1,
            )
            if by_name:
                return by_name
        return PT.browse()

    @api.model
    def quote_inherit_image_from_donor(self, target_code, overwrite=False):
        """Copy main + gallery images onto one SKU from base-MTM or same-name donor."""
        PT = self.sudo().with_context(active_test=False)
        tgt = PT.search([("default_code", "=ilike", (target_code or "").strip())], limit=1)
        if not tgt:
            return {"error": "target_not_found", "sku": target_code}
        if tgt.image_1920 and not overwrite:
            return {"skipped": "already_has_image", "sku": tgt.default_code}
        donor = tgt._quote_image_donor_for()
        if not donor:
            return {"skipped": "no_donor", "sku": tgt.default_code, "name": tgt.name}
        return self.quote_copy_product_images(
            donor.default_code, [tgt.default_code], overwrite=True
        )

    @api.model
    def quote_restore_missing_images(self, dry_run=False, sale_ok_only=True):
        """Fill image-less shop products from same base MTM or same product name."""
        domain = [("image_1920", "=", False), ("active", "=", True)]
        if sale_ok_only:
            domain.append(("sale_ok", "=", True))
        targets = self.sudo().with_context(active_test=False).search(domain)
        copied = []
        no_donor = []
        for tgt in targets:
            donor = tgt._quote_image_donor_for()
            if not donor:
                no_donor.append({"sku": tgt.default_code, "name": tgt.name})
                continue
            if dry_run:
                copied.append({
                    "target": tgt.default_code,
                    "name": tgt.name,
                    "from": donor.default_code,
                })
                continue
            self.quote_copy_product_images(
                donor.default_code, [tgt.default_code], overwrite=True
            )
            copied.append({
                "target": tgt.default_code,
                "name": tgt.name,
                "from": donor.default_code,
            })
        return {
            "dry_run": dry_run,
            "copied": len(copied),
            "no_donor": len(no_donor),
            "copied_details": copied,
            "no_donor_details": no_donor,
        }

    @api.model
    def _rw_cmos_attr(self):
        return self.env.ref("quote_manage_ui.attr_cmos", raise_if_not_found=False)

    def _rw_cmos_status(self):
        """Return CMOS gate for shop sync: None = no CMOS line (leave publish alone)."""
        self.ensure_one()
        attr = self._rw_cmos_attr()
        if not attr:
            return None
        line = self.attribute_line_ids.filtered(lambda l: l.attribute_id == attr)[:1]
        if not line:
            return None
        names = [n for n in line.value_ids.mapped("name") if n]
        if not names:
            return ""
        val = names[0]
        if val == "Successful":
            return "Successful"
        if val == "Failed":
            return "Failed"
        return val

    def _rw_sync_shop_from_cmos(self):
        """CMOS gate + CMOSFL approval merges stock into -CMOSP shop master."""
        Importer = self.env["product.csv.importer"]
        for tmpl in self.with_context(rw_skip_cmos_shop_sync=True):
            if tmpl.type != "product":
                continue
            status = tmpl._rw_cmos_status()
            if status is None:
                continue
            code = (tmpl.default_code or "").strip()

            if Importer._is_cmos_fail_bucket_sku(code):
                if status == "Successful":
                    Importer.transfer_cmos_fail_bucket_to_pass(tmpl)
                elif (
                    tmpl.website_published
                    or tmpl.sale_ok
                ):
                    tmpl.write({"website_published": False, "sale_ok": False})
                continue

            if Importer._is_cmos_pass_bucket_sku(code):
                publish = status == "Successful" and tmpl.qty_available > 0
                vals = {
                    "website_published": publish,
                    "sale_ok": publish,
                }
                if (
                    tmpl.website_published != vals["website_published"]
                    or tmpl.sale_ok != vals["sale_ok"]
                ):
                    tmpl.write(vals)
                continue

            if status == "Successful":
                vals = {"website_published": True, "sale_ok": True}
            else:
                vals = {"website_published": False, "sale_ok": False}
            if (
                tmpl.website_published != vals["website_published"]
                or tmpl.sale_ok != vals["sale_ok"]
            ):
                tmpl.write(vals)

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("rw_skip_cmos_shop_sync") and "attribute_line_ids" in vals:
            self._rw_sync_shop_from_cmos()
        return res

    @api.model
    def _rw_shop_display_code(self, code):
        """Customer-facing MTM — strip internal -BT70 / -4G-256G-N inventory suffixes."""
        code = (code or "").strip()
        if not code or code.startswith("RW-SERIES-"):
            return code
        changed = True
        while changed:
            changed = False
            for suffix in ("-BT70", "-BTU70", "-CMOSP", "-CMOSFL"):
                if code.endswith(suffix):
                    code = code[: -len(suffix)]
                    changed = True
                    break
        m = re.match(r"^(.+)-\d+G-\d+G-[TN]$", code, re.I)
        if m:
            code = m.group(1)
        return code

    def _rw_shop_model_label(self):
        """MTM / model code shown under the product name on the shop (not the product title)."""
        self.ensure_one()
        name = (self.name or "").strip()
        desc = (self.description_sale or "").strip()
        display_desc = self._rw_shop_display_code(desc) if desc else ""
        if display_desc and display_desc != name and not desc.lower().startswith("imported sheet"):
            return display_desc

        code = self._rw_shop_display_code(self.default_code or "")
        if code and code != name:
            return code

        variant_codes = sorted(
            {
                self._rw_shop_display_code(c)
                for c in self.product_variant_ids.mapped("default_code")
                if c and not c.startswith("RW-SERIES-")
            }
        )
        variant_codes = [c for c in variant_codes if c and c != name]
        if len(variant_codes) == 1:
            return variant_codes[0]
        if variant_codes:
            return ", ".join(variant_codes[:4])

        m = re.search(r"SKU\s+(\S+)", desc, re.I)
        if m:
            return self._rw_shop_display_code(m.group(1))
        return code or ""

    def _rw_website_available_qty(self, variant=None):
        """Sellable quantity for the website warehouse.

        * With ``variant``: that configuration only (product detail page).
        * Without ``variant``: sum across all variants (shop list / series total).
        """
        self.ensure_one()
        website = self.env["website"].get_current_website()
        if not website:
            return int(round(self.sudo().qty_available))
        wh = website._get_warehouse_available()
        if variant:
            return int(variant.sudo().with_context(warehouse=wh).free_qty)
        return sum(
            int(v.with_context(warehouse=wh).free_qty)
            for v in self.sudo().product_variant_ids
        )

    def _rw_single_saleable_variant(self):
        """The lone purchasable variant, when this template has exactly one."""
        self.ensure_one()
        variants = self.product_variant_ids.filtered(lambda v: v.active and v.sale_ok)
        return variants if len(variants) == 1 else self.env["product.product"]

    def _get_variant_for_combination(self, combination):
        single = self._rw_single_saleable_variant()
        if single:
            return single
        return super()._get_variant_for_combination(combination)

    def _is_combination_possible(self, combination, parent_combination=None, ignore_no_variant=False):
        single = self._rw_single_saleable_variant()
        if single:
            return True
        return super()._is_combination_possible(
            combination=combination,
            parent_combination=parent_combination,
            ignore_no_variant=ignore_no_variant,
        )
