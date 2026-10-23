# -*- coding: utf-8 -*-
"""1.0.198 — Website cart debug logging (opt-in)."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.registry.clear_cache()
