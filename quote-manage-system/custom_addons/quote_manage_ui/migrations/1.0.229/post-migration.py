# -*- coding: utf-8 -*-
"""1.0.229 — Re-sync header templates (drop stale COW "Refurbished computers" nav)."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    View = env["ir.ui.view"]
    for key in ("template_header_default_force", "template_header_mobile_force"):
        if hasattr(View, "_quote_manage_ui_sync_single_template_from_xml"):
            View._quote_manage_ui_sync_single_template_from_xml(key)
    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()
