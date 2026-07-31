# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    square_enabled = fields.Boolean(
        string='Enable Square Payments',
        help='Allow Pay with Square on Sales Orders for this company.',
    )
    square_payment_mode = fields.Selection(
        [
            ('reader', 'Square Reader (phone/tablet app)'),
            ('terminal', 'Square Terminal (cloud device)'),
        ],
        string='Square Hardware Mode',
        default='reader',
        required=True,
        help='Reader mode: Odoo creates a pending charge; the store phone app '
             'takes payment on the Bluetooth Reader and reports back.',
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
    square_application_id = fields.Char(
        string='Square Application ID',
        groups='base.group_system',
        help='Required by the Mobile Payments SDK on the phone/tablet app.',
    )
    square_location_id = fields.Char(
        string='Square Location ID',
        groups='base.group_system',
    )
    square_device_id = fields.Char(
        string='Square Terminal Device ID',
        groups='base.group_system',
        help='Only for Terminal mode. Paired Terminal device_id (not the 6-digit code).',
    )
    square_mobile_api_key = fields.Char(
        string='Reader App API Key',
        groups='base.group_system',
        help='Shared secret the phone/tablet app sends as Authorization: Bearer … '
             'to fetch pending checkouts from Odoo.',
    )
    square_webhook_signature_key = fields.Char(
        string='Square Webhook Signature Key',
        groups='base.group_system',
        help='Optional. Used to verify Square webhooks.',
    )
    square_journal_id = fields.Many2one(
        'account.journal',
        string='Square Payment Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', id)]",
        help='Bank/cash journal used when posting Square card payments. '
             'Defaults to the first bank journal if empty.',
    )
