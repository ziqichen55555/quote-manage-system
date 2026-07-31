# -*- coding: utf-8 -*-

import secrets
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SquareReaderCheckout(models.Model):
    _name = 'square.reader.checkout'
    _description = 'Square Reader pending checkout'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='sale_order_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        readonly=True,
    )
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    state = fields.Selection(
        [
            ('waiting', 'Waiting on Reader App'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
            ('failed', 'Failed'),
        ],
        default='waiting',
        required=True,
        index=True,
    )
    access_token = fields.Char(
        string='Access Token',
        required=True,
        copy=False,
        index=True,
        default=lambda self: secrets.token_urlsafe(24),
    )
    square_payment_id = fields.Char(string='Square Payment ID', copy=False, index=True)
    status_message = fields.Char(string='Status Message')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                order = self.env['sale.order'].browse(vals.get('sale_order_id'))
                vals['name'] = 'SQ-%s-%s' % (order.name or 'SO', uuid.uuid4().hex[:6].upper())
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(24)
        return super().create(vals_list)

    def action_cancel(self):
        for rec in self.filtered(lambda r: r.state == 'waiting'):
            rec.write({
                'state': 'cancelled',
                'status_message': _('Cancelled from Odoo'),
            })

    def action_mark_paid(self, square_payment_id):
        """Fulfill SO accounting and mark this checkout paid (idempotent)."""
        self.ensure_one()
        if self.state == 'paid':
            return self.env['account.payment']
        if self.state != 'waiting':
            raise UserError(_('Checkout %s is not waiting (state=%s).') % (self.name, self.state))
        if not square_payment_id:
            raise UserError(_('Square payment id is required.'))

        # Prevent double-fulfill if same Square payment already posted.
        existing = self.env['account.payment'].sudo().search([
            ('square_payment_id', '=', square_payment_id),
        ], limit=1)
        if existing:
            self.write({
                'state': 'paid',
                'square_payment_id': square_payment_id,
                'status_message': _('Already recorded as %s') % existing.name,
            })
            return existing

        payments = self.sale_order_id._square_fulfill_after_payment(
            {'id': self.name, 'source': 'reader_app'},
            square_payment_id,
        )
        self.write({
            'state': 'paid',
            'square_payment_id': square_payment_id,
            'status_message': _('Paid via Reader App'),
        })
        return payments
