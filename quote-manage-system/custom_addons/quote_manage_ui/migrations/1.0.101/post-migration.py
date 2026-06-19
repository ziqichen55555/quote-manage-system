# -*- coding: utf-8 -*-
"""1.0.101 — Archive all Configuration dropdown listings (incl. ThinkPad T490s)."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "archive_configuration_dropdown_products"):
        Importer.archive_configuration_dropdown_products()
