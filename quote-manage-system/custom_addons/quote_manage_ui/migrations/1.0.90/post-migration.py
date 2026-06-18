# -*- coding: utf-8 -*-
"""1.0.90 — Restore serial tracking on refurb computers (laptops/desktops/series)."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "fix_product_serial_tracking"):
        Importer.fix_product_serial_tracking()
