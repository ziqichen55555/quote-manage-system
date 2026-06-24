# -*- coding: utf-8 -*-
"""1.0.110 — Fix Brand on Dell Latitude / Optiplex etc. (merge Manufacturer bug)."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    brands = series = 0
    if hasattr(Importer, "repair_shop_brand_attrs"):
        brands = Importer.repair_shop_brand_attrs()
    if hasattr(Importer, "repair_shop_filter_series"):
        series = Importer.repair_shop_filter_series()
    cr.commit()
