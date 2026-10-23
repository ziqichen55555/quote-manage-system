# -*- coding: utf-8 -*-
"""1.0.196 — Shop hero SEO-only; cart ghost line fixes."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.registry.clear_cache()
