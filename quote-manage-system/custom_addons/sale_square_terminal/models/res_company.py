# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    square_enabled = fields.Boolean(
        string='Enable Square Terminal',
        help='Allow Pay with Square on Sales Orders for this company.',
    )
    square_environment = fields.Selection(
        [
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        string='Square Environment',
        default='sandbox',
        required=True,
    )
    square_access_token = fields.Char(
        string='Square Access Token',
        groups='base.group_system',
        help='Personal access token or OAuth access token with PAYMENTS_WRITE.',
    )
    square_location_id = fields.Char(
        string='Square Location ID',
        groups='base.group_system',
    )
    square_device_id = fields.Char(
        string='Square Device ID',
        groups='base.group_system',
        help='Paired Terminal device_id from Devices API (not the 6-digit pair code).',
    )
    square_webhook_signature_key = fields.Char(
        string='Square Webhook Signature Key',
        groups='base.group_system',
        help='Optional. Used to verify terminal.checkout.updated webhooks.',
    )
    square_journal_id = fields.Many2one(
        'account.journal',
        string='Square Payment Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', id)]",
        help='Bank/cash journal used when posting Square card payments. '
             'Defaults to the first bank journal if empty.',
    )
