# -*- coding: utf-8 -*-
"""1.0.91 — Preserve list_price when CSV cost_ex is blank; serial tracking fixes."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "fix_product_serial_tracking"):
        Importer.fix_product_serial_tracking()
