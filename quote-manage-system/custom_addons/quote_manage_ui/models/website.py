# -*- coding: utf-8 -*-
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ormcache

from odoo.addons.quote_manage_ui.website_cart_debug import (
    cart_debug_log,
    sale_order_cart_debug_dict,
)


class Website(models.Model):
    _inherit = "website"

    @ormcache("self.env.uid", "self.id", cache="templates")
    def _get_menu_ids(self):
        """Return live menu ids only (stale ormcache can reference deleted menus)."""
        ids = self.env["website.menu"].search([("website_id", "=", self.id)]).ids
        return self.env["website.menu"].browse(ids).exists().ids

    def _compute_menu(self):
        """Build menu tree from existing records only (avoids MissingError on deleted ids)."""
        for website in self:
            menus = self.env["website.menu"].browse(website._get_menu_ids()).exists()
            for menu in menus:
                menu._cache["child_id"] = ()
            for menu in menus:
                if menu.parent_id and menu.parent_id in menus:
                    menu.parent_id._cache["child_id"] += (menu.id,)
            menus.mapped("is_visible")
            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.menu_id = top_menus and top_menus[0].id or False

    @api.model
    def _quote_clear_website_menu_template_cache(self):
        """Call on module upgrade after menu/category cleanup."""
        Website = self.sudo()
        try:
            Website._get_menu_ids.clear_cache(Website)
        except (TypeError, AttributeError):
            pass
        for site in Website.search([]):
            try:
                Website._get_menu_ids.clear_cache(site)
            except (TypeError, AttributeError):
                pass
        self.env.registry.clear_cache()

    def _reware_structured_data_dict(self):
        """Schema.org graph for brand disambiguation (head only, not reware.world)."""
        self.ensure_one()
        base = (self.domain or "https://www.reware-project.com").rstrip("/")
        org_id = f"{base}/#organization"
        website_id = f"{base}/#website"
        return {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": org_id,
                    "name": "Re-Ware",
                    "alternateName": [
                        "Re-Ware Project",
                        "Reware Project",
                        "reware project",
                        "Re Ware",
                        "re ware",
                        "Re-Ware Co-Creative IT",
                        "Reware Perth",
                    ],
                    "url": base,
                    "logo": f"{base}/web/image/website/{self.id}/logo",
                    "description": (
                        "Re-Ware Project by Co-Creative IT — refurbished and "
                        "second-hand computers, laptops, monitors, cables and "
                        "IT equipment in Perth, Western Australia."
                    ),
                    "parentOrganization": {
                        "@type": "Organization",
                        "name": "Co-Creative IT",
                        "url": "https://www.cocreativeit.com",
                    },
                    "sameAs": [
                        "https://www.cocreativeit.com/reware",
                        "https://www.cocreativeit.com/",
                    ],
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "102 Edward St",
                        "addressLocality": "Perth",
                        "addressRegion": "WA",
                        "postalCode": "6000",
                        "addressCountry": "AU",
                    },
                    "areaServed": {"@type": "Country", "name": "Australia"},
                },
                {
                    "@type": "WebSite",
                    "@id": website_id,
                    "url": base,
                    "name": "Re-Ware Project",
                    "alternateName": ["reware-project.com", "Re-Ware Shop"],
                    "publisher": {"@id": org_id},
                    "inLanguage": "en-AU",
                    "potentialAction": {
                        "@type": "SearchAction",
                        "target": {
                            "@type": "EntryPoint",
                            "urlTemplate": f"{base}/shop?search={{search_term_string}}",
                        },
                        "query-input": "required name=search_term_string",
                    },
                },
                {
                    "@type": "Store",
                    "@id": f"{base}/#store",
                    "name": "Re-Ware Shop",
                    "url": f"{base}/shop",
                    "parentOrganization": {"@id": org_id},
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": "Perth",
                        "addressRegion": "WA",
                        "addressCountry": "AU",
                    },
                },
            ],
        }

    def reware_structured_data_json_str(self):
        self.ensure_one()
        return json.dumps(self._reware_structured_data_dict(), ensure_ascii=False)

    def _quote_reset_website_cart_session(self):
        if request and request.session:
            request.session.pop("sale_order_id", None)
            request.session.pop("website_sale_cart_quantity", None)

    def sale_reset(self):
        """Do not wipe session when DB still has product lines (freight / cache glitches)."""
        sale_order_id = request.session.get("sale_order_id") if request else None
        if sale_order_id:
            order = (
                self.env["sale.order"]
                .sudo()
                .browse(sale_order_id)
                .exists()
            )
            if order.website_id and order._quote_website_product_cart_lines():
                order.invalidate_recordset(
                    ["website_order_line", "cart_quantity", "only_services"]
                )
                qty = order.cart_quantity or int(
                    sum(
                        order._quote_website_product_cart_lines().mapped(
                            "product_uom_qty"
                        )
                    )
                )
                request.session["sale_order_id"] = order.id
                request.session["website_sale_cart_quantity"] = qty
                cart_debug_log(
                    self.env,
                    "sale_reset.blocked",
                    order_id=order.id,
                    session_qty=qty,
                )
                return
        super().sale_reset()

    def _quote_sync_website_cart_session(self, order):
        """Header badge reads session qty first — keep it aligned with the SO."""
        if not request or not request.session:
            return
        prev_qty = request.session.get("website_sale_cart_quantity")
        prev_so = request.session.get("sale_order_id")
        if (
            order
            and order.exists()
            and order.state == "draft"
            and (not order.website_id or order.website_id == self)
        ):
            order_sudo = order.sudo()
            order_sudo._quote_website_repair_cart()
            request.session["sale_order_id"] = order_sudo.id
            request.session["website_sale_cart_quantity"] = order_sudo.cart_quantity
            cart_debug_log(
                self.env,
                "cart_sync",
                prev_sale_order_id=prev_so,
                prev_session_qty=prev_qty,
                sale_order_id=order_sudo.id,
                session_qty=order_sudo.cart_quantity,
                **sale_order_cart_debug_dict(order_sudo),
            )
        else:
            self._quote_reset_website_cart_session()
            cart_debug_log(
                self.env,
                "cart_sync.reset",
                prev_sale_order_id=prev_so,
                prev_session_qty=prev_qty,
                order_id=order.id if order and order.exists() else None,
            )

    def sale_get_order(self, force_create=False, update_pricelist=False):
        """Drop session cart when SO missing, not draft, or wrong site (stale line ids)."""
        sale_order_id = request.session.get("sale_order_id") if request else None
        cart_debug_log(
            self.env,
            "sale_get_order.in",
            session_sale_order_id=sale_order_id,
            force_create=force_create,
            update_pricelist=update_pricelist,
        )
        order = super().sale_get_order(
            force_create=force_create, update_pricelist=update_pricelist
        )
        if sale_order_id and not order:
            self._quote_reset_website_cart_session()
            if force_create:
                order = super().sale_get_order(
                    force_create=True, update_pricelist=update_pricelist
                )
            self._quote_sync_website_cart_session(order)
            cart_debug_log(
                self.env,
                "sale_get_order.out",
                branch="session_so_missing",
                order_id=order.id if order else None,
            )
            return order
        if not order:
            self._quote_sync_website_cart_session(order)
            cart_debug_log(self.env, "sale_get_order.out", branch="empty")
            return order
        if order.state != "draft" or (order.website_id and order.website_id != self):
            self._quote_reset_website_cart_session()
            if force_create:
                order = super().sale_get_order(
                    force_create=True, update_pricelist=update_pricelist
                )
            else:
                order = self.env["sale.order"]
            self._quote_sync_website_cart_session(order)
            cart_debug_log(
                self.env,
                "sale_get_order.out",
                branch="not_draft_or_wrong_site",
                order_id=order.id if order else None,
            )
            return order
        order = self.env["sale.order"].browse(order.id).sudo()
        order._quote_website_repair_cart()
        self._quote_sync_website_cart_session(order)
        cart_debug_log(
            self.env,
            "sale_get_order.out",
            branch="draft_ok",
            **sale_order_cart_debug_dict(order),
        )
        return order

    def _reware_itemlist_json_str_for_products(self, products):
        """ItemList JSON-LD for in-stock shop products (shop page only)."""
        self.ensure_one()
        products = products.exists()
        if not products:
            return ""
        base = (self.domain or "https://www.reware-project.com").rstrip("/")
        elements = []
        for pos, product in enumerate(products, start=1):
            path = (product.website_url or "").strip()
            if not path:
                continue
            url = path if path.startswith("http") else f"{base}{path}"
            elements.append({
                "@type": "ListItem",
                "position": pos,
                "url": url,
                "name": (product.name or "").strip() or "Refurbished IT",
            })
        if not elements:
            return ""
        payload = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Re-Ware shop — refurbished & second-hand IT in stock",
            "itemListElement": elements,
        }
        return json.dumps(payload, ensure_ascii=False)
