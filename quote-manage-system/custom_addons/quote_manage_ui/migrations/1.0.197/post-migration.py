# -*- coding: utf-8 -*-
"""1.0.197 — Replace /returns Easy returns placeholders with final policy copy."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Page = env["website.page"].sudo().with_context(active_test=False)
    View = env["ir.ui.view"]

    if hasattr(Page, "_quote_manage_ui_sync_inline_page_archs_from_module_xml"):
        Page._quote_manage_ui_sync_inline_page_archs_from_module_xml()
    if hasattr(View, "_quote_manage_ui_sync_module_templates_from_xml"):
        View._quote_manage_ui_sync_module_templates_from_xml()

    env.registry.clear_cache()
