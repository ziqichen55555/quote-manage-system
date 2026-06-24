# -*- coding: utf-8 -*-
"""1.0.106 — Archive synthetic IMPORT-* test SKUs from the shop."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    archived = 0
    if hasattr(Importer, "archive_synthetic_import_skus"):
        archived = Importer.archive_synthetic_import_skus()
    cr.commit()
