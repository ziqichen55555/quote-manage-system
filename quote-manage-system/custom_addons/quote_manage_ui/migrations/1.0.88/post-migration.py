# -*- coding: utf-8 -*-
"""1.0.88 — Terms, Privacy and Refund legal pages + footer links."""
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
