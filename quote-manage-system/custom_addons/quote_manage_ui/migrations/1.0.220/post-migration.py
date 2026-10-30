# -*- coding: utf-8 -*-
"""1.0.220 — Enable Google Places checkout address autocomplete module."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search([("name", "=", "website_sale_autocomplete")], limit=1)
    if module and module.state != "installed":
        module.button_immediate_install()
