# -*- coding: utf-8 -*-
"""1.0.216 — Freight markup settings; refresh freight when shipping postcode changes."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("quote_manage_ui.shipping_markup_percent", "0")
    icp.set_param("quote_manage_ui.shipping_markup_fixed_ex_gst", "0")
