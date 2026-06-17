# -*- coding: utf-8 -*-
"""1.0.84 — Drop legacy Cart link from My Account dropdown.

Header cart (1.0.83) is the single entry point. The old
``rw_user_dropdown_cart`` inherit can survive on COW ``ir.ui.view`` rows
because module archs are noupdate-locked after first load.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    View = env["ir.ui.view"].sudo().with_context(active_test=False)

    legacy = View.search([("key", "=", "quote_manage_ui.rw_user_dropdown_cart")])
    if legacy:
        legacy.unlink()

    env["ir.model.data"].sudo().search([
        ("module", "=", "quote_manage_ui"),
        ("name", "=", "rw_user_dropdown_cart"),
    ]).unlink()

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
