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
