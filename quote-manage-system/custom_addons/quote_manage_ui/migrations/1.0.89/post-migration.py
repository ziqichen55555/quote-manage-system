# -*- coding: utf-8 -*-
"""1.0.89 — Move Terms page URL away from Odoo core /terms route."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Page = env["website.page"].sudo().with_context(active_test=False)
    View = env["ir.ui.view"]

    page = Page.search([("key", "=", "quote_manage_ui.terms_of_service_page")], limit=1)
    if page:
        page.write({"url": "/terms-of-service", "is_published": True})

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
