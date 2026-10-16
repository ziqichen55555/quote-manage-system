# -*- coding: utf-8 -*-
"""1.0.188 — SEO head t-cache includes website_indexed; ensure homepage indexable."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_ensure_google_indexable()
    env.registry.clear_cache()
