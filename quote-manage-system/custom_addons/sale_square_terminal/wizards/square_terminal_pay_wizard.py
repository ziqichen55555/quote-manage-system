# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_square_terminal import const


class SquareTerminalPayWizard(models.TransientModel):
    _name = 'square.terminal.pay.wizard'
    _description = 'Pay Sales Order with Square'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        readonly=True,
    )
    amount = fields.Monetary(string='Amount', required=True, readonly=True)
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        readonly=True,
    )
    company_id = fields.Many2one(
        related='sale_order_id.company_id',
        readonly=True,
    )
    payment_mode = fields.Selection(
        related='company_id.square_payment_mode',
        readonly=True,
    )
    device_id = fields.Char(string='Device ID', readonly=True)
    reader_checkout_id = fields.Many2one(
        'square.reader.checkout',
        string='Reader Checkout',
        readonly=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Ready'),
            ('waiting', 'Waiting on Reader'),
            ('done', 'Paid'),
            ('failed', 'Failed'),
        ],
        default='draft',
        required=True,
    )
    checkout_id = fields.Char(string='Checkout ID', readonly=True)
    square_payment_id = fields.Char(string='Square Payment ID', readonly=True)
    status_message = fields.Text(string='Status', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env['sale.order'].browse(
            res.get('sale_order_id') or self.env.context.get('default_sale_order_id')
        )
        if order:
            res.setdefault('amount', order.amount_total)
            res.setdefault('device_id', order.company_id.square_device_id)
        return res

    def action_send_to_reader(self):
        self.ensure_one()
        order = self.sale_order_id
        company = order.company_id
        company._square_require_config()

        if (company.square_payment_mode or 'reader') == 'reader':
            return self._send_reader_pending()
        return self._send_terminal_checkout()

    def _send_reader_pending(self):
        self.ensure_one()
        order = self.sale_order_id
        # Cancel any older waiting checkouts for this SO.
        old = self.env['square.reader.checkout'].search([
            ('sale_order_id', '=', order.id),
            ('state', '=', 'waiting'),
        ])
        old.action_cancel()

        checkout = self.env['square.reader.checkout'].create({
            'sale_order_id': order.id,
            'amount': self.amount,
        })
        self.write({
            'reader_checkout_id': checkout.id,
            'checkout_id': checkout.name,
            'state': 'waiting',
            'status_message': _(
                'Pending charge %s created.\n'
                'On the store phone/tablet app, open the pending payment and take the card on the Square Reader.\n'
                'Then click Check Status here.'
            ) % checkout.name,
        })
        return self._reopen()

    def _send_terminal_checkout(self):
        self.ensure_one()
        order = self.sale_order_id
        company = order.company_id
        checkout = company._square_create_terminal_checkout(
            amount=self.amount,
            currency=order.currency_id,
            reference=order.name,
            note='Odoo SO %s' % order.name,
        )
        self.write({
            'checkout_id': checkout.get('id'),
            'state': 'waiting',
            'status_message': _(
                'Checkout sent to Square Terminal. Ask the customer to tap, insert or swipe. '
                'Then click Check Status.'
            ),
        })
        return self._reopen()

    def action_check_status(self):
        self.ensure_one()
        company = self.sale_order_id.company_id
        if (company.square_payment_mode or 'reader') == 'reader':
            return self._check_reader_status()
        return self._check_terminal_status()

    def _check_reader_status(self):
        self.ensure_one()
        checkout = self.reader_checkout_id
        if not checkout:
            raise UserError(_('No reader checkout in progress. Send to Reader first.'))
        checkout.invalidate_recordset()
        if checkout.state == 'paid':
            self.write({
                'state': 'done',
                'square_payment_id': checkout.square_payment_id,
                'status_message': _('Payment completed via Reader App.'),
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        if checkout.state in ('cancelled', 'failed'):
            self.write({
                'state': 'failed',
                'status_message': checkout.status_message or _('Checkout %s') % checkout.state,
            })
            return self._reopen()
        self.write({
            'state': 'waiting',
            'status_message': _(
                'Still waiting for the store phone app / Reader (checkout %s).'
            ) % checkout.name,
        })
        return self._reopen()

    def _check_terminal_status(self):
        self.ensure_one()
        if not self.checkout_id:
            raise UserError(_('No checkout in progress. Send to Reader first.'))

        company = self.sale_order_id.company_id
        checkout = company._square_get_terminal_checkout(self.checkout_id)
        status = checkout.get('status') or ''
        payment_ids = checkout.get('payment_ids') or []
        payment_id = payment_ids[0] if payment_ids else False

        if status in const.TERMINAL_SUCCESS_STATUSES:
            return self._complete_payment(checkout, payment_id)

        if status in const.TERMINAL_FAILURE_STATUSES:
            self.write({
                'state': 'failed',
                'status_message': _('Checkout %s. You can send a new request.') % status,
            })
            return self._reopen()

        self.write({
            'state': 'waiting',
            'status_message': _('Still waiting on the Terminal (status: %s).') % (status or 'unknown'),
            'square_payment_id': payment_id or self.square_payment_id,
        })
        return self._reopen()

    def action_cancel_checkout(self):
        self.ensure_one()
        company = self.sale_order_id.company_id
        if (company.square_payment_mode or 'reader') == 'reader':
            if self.reader_checkout_id and self.reader_checkout_id.state == 'waiting':
                self.reader_checkout_id.action_cancel()
        elif self.checkout_id and self.state == 'waiting':
            try:
                company._square_cancel_terminal_checkout(self.checkout_id)
            except UserError:
                pass
        self.write({
            'state': 'failed',
            'status_message': _('Checkout cancelled.'),
        })
        return self._reopen()

    def _complete_payment(self, checkout, square_payment_id):
        self.ensure_one()
        payments = self.sale_order_id._square_fulfill_after_payment(
            checkout,
            square_payment_id,
        )
        self.write({
            'state': 'done',
            'square_payment_id': square_payment_id,
            'status_message': _(
                'Payment completed. Recorded payment(s): %s'
            ) % (', '.join(payments.mapped('name')) or _('none')),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
