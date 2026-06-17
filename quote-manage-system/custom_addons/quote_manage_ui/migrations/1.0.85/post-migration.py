# -*- coding: utf-8 -*-
"""1.0.85 — Single-variant shop fix + warehouse-aware stock display."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()
    try:
        env.registry.clear_cache()
    except Exception:
        pass
