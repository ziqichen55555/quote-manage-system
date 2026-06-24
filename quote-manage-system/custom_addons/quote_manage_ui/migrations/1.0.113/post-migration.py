# -*- coding: utf-8 -*-
"""1.0.113 — Merge M91p RW-4518PT1 + 4518PT1 into one product (3 serials)."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    if hasattr(Importer, "repair_m91p_product_merge"):
        Importer.repair_m91p_product_merge()
    cr.commit()
