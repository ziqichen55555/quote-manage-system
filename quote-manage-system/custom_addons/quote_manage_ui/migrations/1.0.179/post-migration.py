# -*- coding: utf-8 -*-
"""1.0.179 — SEO metadata (head tags only): homepage, shop categories, key pages."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_apply_seo_metadata()
