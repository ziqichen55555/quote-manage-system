# -*- coding: utf-8 -*-
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ormcache


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

    def sale_get_order(self, force_create=False, update_pricelist=False):
        """Drop session cart when SO missing, not draft, or wrong site (stale line ids)."""
        sale_order_id = request.session.get("sale_order_id") if request else None
        order = super().sale_get_order(
            force_create=force_create, update_pricelist=update_pricelist
        )
        if sale_order_id and not order:
            self._quote_reset_website_cart_session()
            if force_create:
                order = super().sale_get_order(
                    force_create=True, update_pricelist=update_pricelist
                )
            return order
        if not order:
            return order
        if order.state != "draft" or (order.website_id and order.website_id != self):
            self._quote_reset_website_cart_session()
            if force_create:
                return super().sale_get_order(
                    force_create=True, update_pricelist=update_pricelist
                )
            return self.env["sale.order"]
        order.sudo()._quote_website_repair_cart()
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
