# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_square_terminal import const


class SquareRefundWizard(models.TransientModel):
    _name = 'square.refund.wizard'
    _description = 'Refund credit note via Square'

    move_id = fields.Many2one(
        'account.move',
        string='Credit Note',
        required=True,
        readonly=True,
        domain=[('move_type', 'in', ('out_refund', 'in_refund'))],
    )
    source_payment_id = fields.Many2one(
        'account.payment',
        string='Original Square Payment',
        required=True,
        domain="[('square_payment_id', '!=', False), ('payment_type', '=', 'inbound')]",
    )
    amount = fields.Monetary(string='Refund Amount', required=True)
    currency_id = fields.Many2one(related='move_id.currency_id', readonly=True)
    reason = fields.Char(string='Reason')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = self.env['account.move'].browse(
            res.get('move_id') or self.env.context.get('default_move_id')
        )
        if not move:
            return res
        res.setdefault('amount', abs(move.amount_residual))
        # Prefer payments linked via reversed invoice / sale order.
        payments = self.env['account.payment']
        origin_invoices = move.reversed_entry_id
        if origin_invoices:
            payments = origin_invoices._get_reconciled_payments().filtered('square_payment_id')
        if not payments and move.invoice_line_ids.sale_line_ids:
            orders = move.invoice_line_ids.sale_line_ids.order_id
            so_invoices = orders.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
            )
            payments = so_invoices._get_reconciled_payments().filtered('square_payment_id')
        if payments:
            res.setdefault('source_payment_id', payments[0].id)
        return res

    def action_refund(self):
        self.ensure_one()
        move = self.move_id
        payment = self.source_payment_id
        if not payment.square_payment_id:
            raise UserError(_('Selected payment has no Square Payment ID.'))
        if self.amount <= 0:
            raise UserError(_('Refund amount must be greater than zero.'))
        if self.amount > abs(move.amount_residual) + 0.00001:
            raise UserError(_('Refund amount cannot exceed the credit note residual.'))

        company = move.company_id
        refund = company._square_refund_payment(
            payment_id=payment.square_payment_id,
            amount=self.amount,
            currency=move.currency_id,
            reason=self.reason or move.name,
        )
        status = refund.get('status')
        if status in (const.REFUND_STATUS_FAILED, const.REFUND_STATUS_REJECTED):
            raise UserError(_('Square refund failed (status: %s).') % status)

        journal = company.square_journal_id or payment.journal_id
        method_line = journal.outbound_payment_method_line_ids.filtered(
            lambda l: l.code == 'square'
        )[:1]
        if not method_line:
            self.env['account.payment.method']._ensure_square_method_lines()
            method_line = journal.outbound_payment_method_line_ids.filtered(
                lambda l: l.code == 'square'
            )[:1]
        if not method_line:
            raise UserError(_('Square Refund payment method missing on journal %s.') % journal.display_name)

        register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create({
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
            'amount': self.amount,
            'communication': move.name,
        })
        odoo_payment = register._create_payments()
        odoo_payment.write({
            'square_payment_id': payment.square_payment_id,
            'square_refund_id': refund.get('id'),
        })

        msg = _('Square refund %s (status: %s). Odoo payment: %s') % (
            refund.get('id'),
            status,
            odoo_payment.name,
        )
        move.message_post(body=msg)
        return {'type': 'ir.actions.act_window_close'}
