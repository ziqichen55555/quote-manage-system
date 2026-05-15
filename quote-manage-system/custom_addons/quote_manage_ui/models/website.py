# -*- coding: utf-8 -*-
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
