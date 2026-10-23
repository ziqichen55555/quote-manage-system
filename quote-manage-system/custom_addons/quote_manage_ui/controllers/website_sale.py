# -*- coding: utf-8 -*-
"""Website shop: guest or registered checkout; contact + billing address before payment."""
import json

from odoo import _, http
from odoo.addons.website_sale.controllers import main as website_sale_controller
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.tools import lazy
from odoo.addons.quote_manage_ui.website_cart_debug import (
    build_cart_debug_payload,
    cart_debug_enabled,
    cart_debug_log,
)


class WebsiteSale(website_sale_controller.WebsiteSale):
    def cart(self, access_token=None, revive="", **post):
        cart_debug_log(request.env, "route.cart.in", access_token=bool(access_token))
        try:
            res = super().cart(
                access_token=access_token, revive=revive, **post
            )
            cart_debug_log(request.env, "route.cart.out", ok=True)
            return res
        except MissingError as err:
            cart_debug_log(request.env, "route.cart.missing", error=str(err))
            so_id = request.session.get("sale_order_id")
            if so_id:
                request.env["sale.order"].sudo().browse(so_id).exists()._quote_website_repair_cart()
            try:
                return super().cart(
                    access_token=access_token, revive=revive, **post
                )
            except MissingError:
                so_id = request.session.get("sale_order_id")
                order = (
                    request.env["sale.order"].sudo().browse(so_id).exists()
                    if so_id
                    else request.env["sale.order"]
                )
                if order and order._quote_website_product_cart_lines():
                    order._quote_website_repair_cart()
                    request.website._quote_sync_website_cart_session(order)
                else:
                    request.website._quote_reset_website_cart_session()
                return request.redirect("/shop/cart")

    def cart_update_json(
        self,
        product_id,
        line_id=None,
        add_qty=None,
        set_qty=None,
        display=True,
        product_custom_attribute_values=None,
        no_variant_attribute_values=None,
        **kw,
    ):
        cart_debug_log(
            request.env,
            "route.cart_update_json.in",
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
        )
        try:
            out = super().cart_update_json(
                product_id,
                line_id=line_id,
                add_qty=add_qty,
                set_qty=set_qty,
                display=display,
                product_custom_attribute_values=product_custom_attribute_values,
                no_variant_attribute_values=no_variant_attribute_values,
                **kw,
            )
            cart_debug_log(
                request.env,
                "route.cart_update_json.out",
                cart_quantity=out.get("cart_quantity") if isinstance(out, dict) else None,
            )
            return out
        except MissingError as err:
            cart_debug_log(
                request.env,
                "route.cart_update_json.missing",
                error=str(err),
            )
            so_id = request.session.get("sale_order_id")
            order = (
                request.env["sale.order"].sudo().browse(so_id).exists()
                if so_id
                else request.env["sale.order"]
            )
            retry_line_id = line_id
            if order:
                order._quote_website_repair_cart()
                retry_line_id = order._quote_resolve_cart_line_id(
                    product_id, line_id=line_id
                )
                request.website._quote_sync_website_cart_session(order)
            try:
                out = super().cart_update_json(
                    product_id,
                    line_id=retry_line_id,
                    add_qty=add_qty,
                    set_qty=set_qty,
                    display=display,
                    product_custom_attribute_values=product_custom_attribute_values,
                    no_variant_attribute_values=no_variant_attribute_values,
                    **kw,
                )
                cart_debug_log(
                    request.env,
                    "route.cart_update_json.out_after_retry",
                    cart_quantity=out.get("cart_quantity")
                    if isinstance(out, dict)
                    else None,
                )
                return out
            except MissingError:
                request.website._quote_reset_website_cart_session()
                raise

    @http.route(
        ["/shop/cart/debug"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def quote_cart_debug(self, **kw):
        """JSON cart snapshot when quote_manage_ui.website_cart_debug=1 (guest OK)."""
        if not cart_debug_enabled(request.env):
            return request.make_response(
                "Cart debug is off. Set system parameter "
                "quote_manage_ui.website_cart_debug = 1 (or "
                "QUOTE_WEBSITE_CART_DEBUG=1 on the server).\n",
                status=403,
                headers=[("Content-Type", "text/plain; charset=utf-8")],
            )
        payload = build_cart_debug_payload(request.env)
        return request.make_response(
            json.dumps(payload, indent=2, default=str),
            headers=[("Content-Type", "application/json; charset=utf-8")],
        )

    @http.route(
        ["/quote-cart-debug"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def quote_cart_debug_alias(self, **kw):
        """Same JSON as /shop/cart/debug (easier to spot if shop routes 404)."""
        return self.quote_cart_debug(**kw)

    def _cart_values(self, **post):
        values = super()._cart_values(**post)
        if cart_debug_enabled(request.env):
            values["quote_cart_debug_json"] = json.dumps(
                build_cart_debug_payload(request.env),
                indent=2,
                default=str,
            )
        return values

    def shop(self, page=0, category=None, search="", **post):
        try:
            return super().shop(
                page=page, category=category, search=search, **post
            )
        except MissingError:
            request.website._quote_reset_website_cart_session()
            return super().shop(
                page=page, category=category, search=search, **post
            )

    def _get_mandatory_fields_billing(self, country_id=False):
        """Re-Ware: phone and postcode always required; street2 optional (houses have none)."""
        req = super()._get_mandatory_fields_billing(country_id)
        for fname in ("phone", "zip"):
            if fname not in req:
                req.append(fname)
        return req

    def _get_mandatory_fields_shipping(self, country_id=False):
        req = super()._get_mandatory_fields_shipping(country_id)
        if "zip" not in req:
            req.append("zip")
        return req

    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        if order:
            order.sudo()._rw_ensure_default_freight()
        return super().shop_payment(**post)

    def _get_shop_payment_errors(self, order):
        errors = super()._get_shop_payment_errors(order)
        if not order:
            return errors
        if not order._quote_has_contactable_customer():
            errors.append((
                _("Customer details required"),
                _(
                    "Please complete your name, email, phone and billing address "
                    "before placing a quotation or paying."
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

    def _quote_seo_in_stock_products(self, category=None, limit=24):
        PT = request.env["product.template"].sudo()
        return PT._rw_website_in_stock_published(limit=limit, category=category)

    def _get_additional_extra_shop_values(self, values, **post):
        res = super()._get_additional_extra_shop_values(values, **post)
        values["categories"] = lazy(
            lambda: self._quote_wsale_root_categories_with_products()
        )
        category = values.get("category")
        cat_record = category if category and category.id else None
        res["quote_seo_in_stock_products"] = lazy(
            lambda: self._quote_seo_in_stock_products(category=cat_record, limit=24)
        )
        res["quote_seo_itemlist_json"] = lazy(
            lambda: request.website.sudo()._reware_itemlist_json_str_for_products(
                self._quote_seo_in_stock_products(category=cat_record, limit=12)
            )
        )
        if not cat_record:
            res.update({
                "title": (
                    "Second-Hand & Refurbished Computers | Re-Ware Shop Australia"
                ),
                "website_meta_description": (
                    "Shop second-hand and refurbished computers at Re-Ware "
                    "(reware-project.com): ex-lease laptops, desktops, monitors "
                    "and IT in Perth. Graded, tested, warranty — Australia-wide."
                ),
            })
            in_stock = self._quote_seo_in_stock_products(limit=8)
            snippet = request.env["product.template"].sudo()._rw_seo_meta_snippet_for_products(
                in_stock, max_names=6
            )
            if snippet:
                res["website_meta_description"] = (
                    res["website_meta_description"] + snippet
                )[:320]
        elif not (category.website_meta_title or "").strip():
            res.update({
                "title": category._rw_seo_category_default_title(),
            })
        if cat_record and not (category.website_meta_description or "").strip():
            desc = category._rw_seo_category_default_description()
            in_stock = self._quote_seo_in_stock_products(category=cat_record, limit=8)
            snippet = request.env["product.template"].sudo()._rw_seo_meta_snippet_for_products(
                in_stock, max_names=6
            )
            res["website_meta_description"] = (desc + snippet)[:320]
        elif cat_record and (category.website_meta_description or "").strip():
            in_stock = self._quote_seo_in_stock_products(category=cat_record, limit=6)
            snippet = request.env["product.template"].sudo()._rw_seo_meta_snippet_for_products(
                in_stock, max_names=4, max_len=120
            )
            if snippet:
                res["website_meta_description"] = (
                    (category.website_meta_description or "") + snippet
                )[:320]
        return res

    def _prepare_product_values(self, product, category="", search="", **kwargs):
        out = super()._prepare_product_values(product, category, search, **kwargs)
        out["categories"] = lazy(
            lambda: self._quote_wsale_root_categories_with_products()
        )
        if not (product.website_meta_title or "").strip():
            out["title"] = product._rw_seo_default_title()
        if not (product.website_meta_description or "").strip():
            out["website_meta_description"] = product._rw_seo_default_description()
        return out
