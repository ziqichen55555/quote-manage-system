# -*- coding: utf-8 -*-
"""1.0.156 — Add Book. link to website header navigation."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['website.page']._quote_manage_ui_cleanup_duplicate_menus()
