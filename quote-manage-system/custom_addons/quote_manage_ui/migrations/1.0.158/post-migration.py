# -*- coding: utf-8 -*-
"""1.0.158 — Move booking entry from header to Contact page CTA."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['website.page']._quote_manage_ui_cleanup_duplicate_menus()
    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
