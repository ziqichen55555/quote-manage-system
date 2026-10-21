# -*- coding: utf-8 -*-
"""1.0.192 — Shop nav/hero SEO: internal links and commercial headings."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website"]._quote_clear_website_menu_template_cache()
    env.registry.clear_cache()
