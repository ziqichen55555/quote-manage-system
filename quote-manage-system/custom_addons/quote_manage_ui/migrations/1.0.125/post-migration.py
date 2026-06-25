# -*- coding: utf-8 -*-
"""1.0.125: shop shows base MTM only; internal SKU keeps -BT70 / config suffixes."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.csv.importer"].fix_shop_model_subtitles()
