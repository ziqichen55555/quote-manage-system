# -*- coding: utf-8 -*-
from odoo import api, models


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    @api.model
    def _quote_remove_legacy_demo_root_categories(self):
        """Remove orphan demo roots (Smartphones/Tablets/Watches) and duplicate empty Laptops."""
        Category = self.sudo()
        legacy = Category.search(
            [
                ("parent_id", "=", False),
                ("name", "in", ["Smartphones", "Tablets", "Watches"]),
            ]
        )
        if legacy:
            legacy.unlink()

        laptops = Category.search([("parent_id", "=", False), ("name", "=", "Laptops")])
        if len(laptops) > 1:
            with_products = laptops.filtered(lambda c: c.product_tmpl_ids)
            keep = with_products[:1] if with_products else laptops.sorted("id")[:1]
            (laptops - keep).unlink()
