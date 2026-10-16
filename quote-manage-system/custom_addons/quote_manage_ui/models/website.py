# -*- coding: utf-8 -*-
import json

from odoo import api, models
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
