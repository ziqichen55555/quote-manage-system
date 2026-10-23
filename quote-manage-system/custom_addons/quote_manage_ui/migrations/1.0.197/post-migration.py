# -*- coding: utf-8 -*-
"""1.0.197 — Sync website cart session qty; DB-backed cart lines."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.registry.clear_cache()
