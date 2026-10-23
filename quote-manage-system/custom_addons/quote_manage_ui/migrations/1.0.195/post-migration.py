# -*- coding: utf-8 -*-
"""1.0.195 — Hide shop in-stock SEO list; repair stale website cart lines."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.registry.clear_cache()
