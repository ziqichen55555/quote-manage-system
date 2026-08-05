# -*- coding: utf-8 -*-
"""1.0.172 — Remove Square payment methods; add POS Machine for Register Payment."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    square_methods = env['account.payment.method'].sudo().search([
        ('code', '=', 'square'),
    ])
    if square_methods:
        env['account.payment.method.line'].sudo().search([
            ('payment_method_id', 'in', square_methods.ids),
        ]).unlink()

    env['account.payment.method']._ensure_posmachine_method_lines()

    square_module = env['ir.module.module'].search([
        ('name', '=', 'sale_square_terminal'),
        ('state', '=', 'installed'),
    ], limit=1)
    if square_module:
        try:
            square_module.button_immediate_uninstall()
        except Exception:
            square_module.write({'state': 'uninstalled'})
