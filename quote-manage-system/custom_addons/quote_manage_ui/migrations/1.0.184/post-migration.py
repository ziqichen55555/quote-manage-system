# -*- coding: utf-8 -*-
"""1.0.184 — Guest checkout (optional account) + register path on cart."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website"].sudo().search([]).write({"account_on_checkout": "optional"})
