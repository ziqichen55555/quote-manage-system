# -*- coding: utf-8 -*-
"""1.0.109 — Repair shop Series filter attrs (short labels, no Gen suffix)."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    fixed = 0
    if hasattr(Importer, "repair_shop_filter_series"):
        fixed = Importer.repair_shop_filter_series()
    cr.commit()
