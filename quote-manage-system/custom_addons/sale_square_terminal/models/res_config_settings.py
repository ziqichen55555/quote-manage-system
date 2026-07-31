# -*- coding: utf-8 -*-

import secrets

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    square_enabled = fields.Boolean(
        related='company_id.square_enabled',
        readonly=False,
    )
    square_payment_mode = fields.Selection(
        related='company_id.square_payment_mode',
        readonly=False,
    )
    square_environment = fields.Selection(
        related='company_id.square_environment',
        readonly=False,
    )
    square_access_token = fields.Char(
        related='company_id.square_access_token',
        readonly=False,
        groups='base.group_system',
    )
    square_application_id = fields.Char(
        related='company_id.square_application_id',
        readonly=False,
        groups='base.group_system',
    )
    square_location_id = fields.Char(
        related='company_id.square_location_id',
        readonly=False,
        groups='base.group_system',
    )
    square_device_id = fields.Char(
        related='company_id.square_device_id',
        readonly=False,
        groups='base.group_system',
    )
    square_mobile_api_key = fields.Char(
        related='company_id.square_mobile_api_key',
        readonly=False,
        groups='base.group_system',
    )
    square_webhook_signature_key = fields.Char(
        related='company_id.square_webhook_signature_key',
        readonly=False,
        groups='base.group_system',
    )
    square_journal_id = fields.Many2one(
        related='company_id.square_journal_id',
        readonly=False,
    )
    square_webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_square_webhook_url',
    )
    square_reader_api_base = fields.Char(
        string='Reader App API Base URL',
        compute='_compute_square_webhook_url',
    )

    def _compute_square_webhook_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        for wizard in self:
            wizard.square_webhook_url = (
                '%s/square/terminal/webhook' % base if base else '/square/terminal/webhook'
            )
            wizard.square_reader_api_base = base or ''

    def action_square_generate_mobile_api_key(self):
        self.ensure_one()
        key = secrets.token_urlsafe(32)
        self.company_id.sudo().write({'square_mobile_api_key': key})
        self.square_mobile_api_key = key
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reader App API Key'),
                'message': _('New API key generated. Copy it into the phone/tablet app settings, then Save.'),
                'type': 'success',
                'sticky': True,
            },
        }

    def action_square_test_connection(self):
        self.ensure_one()
        self.company_id.sudo().write({
            'square_enabled': self.square_enabled,
            'square_payment_mode': self.square_payment_mode,
            'square_environment': self.square_environment,
            'square_access_token': self.square_access_token,
            'square_application_id': self.square_application_id,
            'square_location_id': self.square_location_id,
            'square_device_id': self.square_device_id,
            'square_mobile_api_key': self.square_mobile_api_key,
            'square_webhook_signature_key': self.square_webhook_signature_key,
            'square_journal_id': self.square_journal_id.id if self.square_journal_id else False,
        })
        message = self.company_id._square_test_connection()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Square connection'),
                'message': message,
                'type': 'success',
                'sticky': True,
            },
        }
