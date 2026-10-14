# -*- coding: utf-8 -*-
"""1.0.183 — Brand JSON-LD, stronger titles, backfill product SEO metadata."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_apply_seo_metadata()
    env["product.template"]._quote_manage_ui_backfill_published_product_seo()
