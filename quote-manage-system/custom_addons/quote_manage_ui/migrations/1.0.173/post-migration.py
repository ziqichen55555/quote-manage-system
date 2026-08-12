# -*- coding: utf-8 -*-
"""1.0.173 — Flag anonymous website carts; require contact before quotation/pay."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Recompute stored flag for existing website carts (Public User partner).
    orders = env["sale.order"].sudo().search([("website_id", "!=", False)])
    if orders:
        orders._compute_quote_is_anonymous_website_cart()
