# -*- coding: utf-8 -*-
from odoo import api, models

# Root eCommerce category display order (Laptops, then Desktops, …).
_SHOP_ROOT_CATEGORY_SEQUENCE = {
    "Laptops": 10,
    "Desktops & Mini PCs": 20,
    "Monitors & Displays": 30,
    "Docks": 40,
    "Accessories": 50,
    "Projectors & AV": 60,
    "Services": 70,
}


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    def _rw_website_stock_units(self):
        """Sellable units in this shop category (sum of on-hand qty)."""
        self.ensure_one()
        products = self.env["product.template"].sudo().search(
            [
                ("public_categ_ids", "in", self.id),
                ("website_published", "=", True),
                ("sale_ok", "=", True),
            ]
        )
        total = 0
        for product in products:
            if product.type == "service":
                total += 1
            else:
                total += product._rw_website_available_qty()
        return int(total)

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

    @api.model
    def repair_shop_public_categories(self):
        """Drop duplicate Laptops › Computer Systems; reorder root categories."""
        Category = self.sudo()
        PT = self.env["product.template"].sudo()
        laptops = Category.search(
            [("name", "=", "Laptops"), ("parent_id", "=", False)], limit=1
        )

        cs_cats = Category.search([("name", "=", "Computer Systems")])
        removed_cs = 0
        for cs in cs_cats:
            for tmpl in PT.search([("public_categ_ids", "in", cs.id)]):
                cmds = [(3, cs.id)]
                if laptops and laptops.id not in tmpl.public_categ_ids.ids:
                    cmds.append((4, laptops.id))
                tmpl.write({"public_categ_ids": cmds})
            cs.unlink()
            removed_cs += 1

        sequenced = 0
        for name, seq in _SHOP_ROOT_CATEGORY_SEQUENCE.items():
            roots = Category.search([("name", "=", name), ("parent_id", "=", False)])
            if roots:
                roots.write({"sequence": seq})
                sequenced += len(roots)

        return {"removed_cs": removed_cs, "sequenced": sequenced}
