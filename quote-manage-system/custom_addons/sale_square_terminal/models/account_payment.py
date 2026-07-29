# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    square_payment_id = fields.Char(
        string='Square Payment ID',
        copy=False,
        index=True,
        help='Square Payments API id used for refunds.',
    )
    square_checkout_id = fields.Char(
        string='Square Checkout ID',
        copy=False,
        index=True,
    )
    square_refund_id = fields.Char(
        string='Square Refund ID',
        copy=False,
        index=True,
    )
