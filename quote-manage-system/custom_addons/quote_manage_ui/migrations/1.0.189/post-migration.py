# -*- coding: utf-8 -*-
"""1.0.189 — Fix SEO head t-cache (only website.page may read website_indexed)."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    View = env["ir.ui.view"]
    if hasattr(View, "_quote_manage_ui_sync_module_templates_from_xml"):
        View._quote_manage_ui_sync_module_templates_from_xml()
    env.registry.clear_cache()
