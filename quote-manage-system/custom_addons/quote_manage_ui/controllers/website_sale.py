# -*- coding: utf-8 -*-
"""Website shop: require account + contact details before quotation/payment."""
from odoo import _
from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.http import request
from odoo.tools import lazy


class WebsiteSale(website_sale_controller.WebsiteSale):
    def checkout_redirection(self, order):
        """Mandatory account: send guests to signup (not guest checkout)."""
        redirection = super().checkout_redirection(order)
        if (
            redirection
            and request.website.account_on_checkout == "mandatory"
            and request.website.is_public_user()
            and "/web/login" in (redirection.location or "")
        ):
            return request.redirect("/web/signup?redirect=/shop/checkout")
        return redirection

    def _get_mandatory_fields_billing(self, country_id=False):
        """Phone required so unpaid quotations remain contactable."""
        req = super()._get_mandatory_fields_billing(country_id)
        if "phone" not in req:
            req.append("phone")
        return req

    def _get_shop_payment_errors(self, order):
        errors = super()._get_shop_payment_errors(order)
        if not order:
            return errors
        if request.website.is_public_user():
            errors.append((
                _("Account required"),
                _(
                    "Please create an account or sign in before placing a "
                    "quotation or paying."
                ),
            ))
        elif not order._quote_has_contactable_customer():
            errors.append((
                _("Customer details required"),
                _(
                    "Please complete your name, email and phone on your account "
                    "or address before placing a quotation or paying."
                ),
            ))
        return errors

    def _quote_wsale_root_categories_with_products(self):
        Category = request.env["product.public.category"].sudo()
        PT = request.env["product.template"].sudo()
        wdom = request.website.website_domain()
        roots = Category.search(
            [("parent_id", "=", False)] + wdom, order="sequence, name, id"
        )
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

    def _quote_attrib_value_ids_for_shop(self, search_product, attrib_set):
        """Attribute value ids actually used by the current listing products.

        Series / Generation / etc. must only show options that exist on real
        shop products — never orphan product.attribute.value rows.
        """
        attrib_set = set(attrib_set or ())
        if search_product is None:
            return attrib_set
        if not search_product:
            return attrib_set
        lines = (
            request.env["product.template.attribute.line"]
            .sudo()
            .search([("product_tmpl_id", "in", search_product.ids)])
        )
        return set(lines.mapped("value_ids").ids) | attrib_set

    def _get_additional_shop_values(self, values):
        res = super()._get_additional_shop_values(values)
        res["quote_attrib_value_ids"] = self._quote_attrib_value_ids_for_shop(
            values.get("search_product"),
            values.get("attrib_set") or set(),
        )
        return res

    def _get_additional_extra_shop_values(self, values, **post):
        res = super()._get_additional_extra_shop_values(values, **post)
        values["categories"] = lazy(
            lambda: self._quote_wsale_root_categories_with_products()
        )
        return res

    def _prepare_product_values(self, product, category="", search="", **kwargs):
        out = super()._prepare_product_values(product, category, search, **kwargs)
        out["categories"] = lazy(
            lambda: self._quote_wsale_root_categories_with_products()
        )
        return out
