# -*- coding: utf-8 -*-
"""1.0.180 — Ensure website domain + website_indexed allow Google crawling."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_ensure_google_indexable()
