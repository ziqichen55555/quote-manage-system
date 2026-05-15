# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import models


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    def _prepare_single_value_for_display(self):
        """Deduplicate attribute lines that share the same attribute and same value.

        Odoo's default groups lines by attribute but concatenates every line's
        value with commas. Duplicate DB rows (same template + attribute + same
        single value) therefore show as ``Lenovo, Lenovo, Lenovo``.
        """
        grouped = super()._prepare_single_value_for_display()
        out = OrderedDict()
        for attr, ptals in grouped.items():
            seen_pav_ids = set()
            kept = self.env["product.template.attribute.line"]
            for ptal in ptals:
                active = ptal.product_template_value_ids._only_active()
                if len(active) != 1:
                    kept |= ptal
                    continue
                pav = active[0].product_attribute_value_id
                key = pav.id if pav else active[0].id
                if key in seen_pav_ids:
                    continue
                seen_pav_ids.add(key)
                kept |= ptal
            out[attr] = kept
        return out
