# -*- coding: utf-8 -*-
"""1.0.105 — Repair 1135GB/1145GB Storage attrs; merge upload refreshes specs."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    fixed = 0
    if hasattr(Importer, "repair_cpu_model_storage_attrs"):
        fixed = Importer.repair_cpu_model_storage_attrs()
    cr.commit()
