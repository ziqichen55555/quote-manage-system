# -*- coding: utf-8 -*-
"""1.0.87 — Retry M910 merge after safe serial-stock migration (1.0.86 deploy failed)."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "fix_thinkcentre_m910_series"):
        Importer.fix_thinkcentre_m910_series()
    if hasattr(Importer, "merge_existing_catalog"):
        Importer.merge_existing_catalog()

    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()

    try:
        env.registry.clear_cache()
    except Exception:
        pass
