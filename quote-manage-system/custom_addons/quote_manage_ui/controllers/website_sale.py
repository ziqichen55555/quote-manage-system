# -*- coding: utf-8 -*-
"""Tighten eCommerce category lists to match real catalogue (same rule as shop hero)."""
from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.http import request
from odoo.tools import lazy


class WebsiteSale(website_sale_controller.WebsiteSale):
    def _quote_wsale_root_categories_with_products(self):
        Category = request.env["product.public.category"].sudo()
        PT = request.env["product.template"].sudo()
        wdom = request.website.website_domain()
        roots = Category.search([("parent_id", "=", False)] + wdom, order="sequence, name, id")
        seen_names = set()
        keep_ids = []
        for c in roots:
            if not PT.search_count(
                [
                    ("public_categ_ids", "in", [c.id]),
                    ("website_published", "=", True),
                    ("sale_ok", "=", True),
                ]
            ):
                continue
            name_key = (c.name or "").strip().casefold()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            keep_ids.append(c.id)
        return Category.browse(keep_ids)

    def _get_additional_extra_shop_values(self, values, **post):
        res = super()._get_additional_extra_shop_values(values, **post)
        values["categories"] = lazy(lambda: self._quote_wsale_root_categories_with_products())
        return res

    def _prepare_product_values(self, product, category="", search="", **kwargs):
        out = super()._prepare_product_values(product, category, search, **kwargs)
        out["categories"] = lazy(lambda: self._quote_wsale_root_categories_with_products())
        return out
