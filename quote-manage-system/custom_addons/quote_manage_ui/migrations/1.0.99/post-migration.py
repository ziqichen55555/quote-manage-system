# -*- coding: utf-8 -*-
"""1.0.99 — Shop subtitle shows MTM/model under product name, not duplicate title."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "fix_shop_model_subtitles"):
        Importer.fix_shop_model_subtitles()
