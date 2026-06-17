# -*- coding: utf-8 -*-
"""1.0.83 — Show cart icon in the site header (not only inside My Account).

Guests need a visible /shop/cart entry in the top nav (mwave-style). The
Re-Ware header fully replaces website.navbar on desktop, so cart is wired in
template_header_default_force; the old portal.user_dropdown cart link is removed.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Page = env["website.page"]
    View = env["ir.ui.view"]

    if hasattr(Page, "_quote_manage_ui_sync_inline_page_archs_from_module_xml"):
        Page._quote_manage_ui_sync_inline_page_archs_from_module_xml()
    if hasattr(View, "_quote_manage_ui_sync_module_templates_from_xml"):
        View._quote_manage_ui_sync_module_templates_from_xml()

    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()

    try:
        env.registry.clear_cache()
    except Exception:
        pass
