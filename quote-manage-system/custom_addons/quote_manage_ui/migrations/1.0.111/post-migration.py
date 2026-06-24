# -*- coding: utf-8 -*-
"""1.0.111 — Consolidate legacy RW-{MTM} duplicate shop products into real MTM SKUs."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    if hasattr(Importer, "consolidate_legacy_rw_skus"):
        Importer.consolidate_legacy_rw_skus()
    cr.commit()
