# -*- coding: utf-8 -*-
"""1.0.77 — Remove duplicate SKU from invoice/SO lines.

Imported products had description_sale = "Imported sheet · SKU <code>".
Odoo already prepends "[<code>] " (the Internal Reference) to each
sale/invoice line, so the SKU was printed twice. The XML no longer sets
description_sale; this migration clears the leftover values already stored
in the database.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    products = env['product.template'].sudo().search([
        ('description_sale', '=like', 'Imported sheet%'),
    ])
    if products:
        products.write({'description_sale': False})
