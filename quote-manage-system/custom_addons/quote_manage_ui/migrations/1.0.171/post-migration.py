# -*- coding: utf-8 -*-
"""1.0.171 — Show lots/serials on invoices (and delivery slips)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["quote.manage.ui.setup"].enable_lots_and_serial_numbers()
