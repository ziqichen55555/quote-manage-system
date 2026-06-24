# -*- coding: utf-8 -*-
"""1.0.115 — Enable Lots & Serial Numbers UI (delivery SN selection)."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["quote.manage.ui.setup"].enable_lots_and_serial_numbers()
