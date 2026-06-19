# -*- coding: utf-8 -*-
"""1.0.100 — One shop product per MTM/SKU; archive old RW-SERIES combined listings."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "archive_series_configuration_products"):
        Importer.archive_series_configuration_products()
