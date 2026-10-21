# -*- coding: utf-8 -*-
"""1.0.193 — Shop SEO: in-stock product links, meta snippet, ItemList JSON-LD."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.registry.clear_cache()
