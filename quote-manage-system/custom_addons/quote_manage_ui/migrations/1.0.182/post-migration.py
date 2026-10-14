# -*- coding: utf-8 -*-
"""1.0.182 — Multi-intent SEO copy (retail, B2B, impact) per page/category."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_apply_seo_metadata()
