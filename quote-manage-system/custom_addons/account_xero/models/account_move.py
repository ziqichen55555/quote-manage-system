# -*- coding: utf-8 -*-

from odoo import _, fields, models

from odoo.addons.account_xero import const


class AccountMove(models.Model):
    _inherit = 'account.move'

    xero_invoice_id = fields.Char(string='Xero Invoice ID', copy=False, index=True)
    xero_sync_status = fields.Selection(
        const.SYNC_STATUS_SELECTION,
        string='Xero Sync Status',
        copy=False,
        readonly=True,
    )
    xero_sync_message = fields.Text(string='Xero Sync Message', copy=False, readonly=True)

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        invoices = posted.filtered(
            lambda move: move.is_sale_document() and move.move_type == 'out_invoice'
        )
        for move in invoices:
            company = move.company_id
            if company.xero_enabled and company.xero_connected:
                company._xero_sync_invoice_safe(move)
                move._xero_sync_reconciled_payments()
        return posted

    def _xero_sync_reconciled_payments(self):
        for move in self:
            payments = move._get_reconciled_payments()
            for payment in payments:
                move.company_id._xero_sync_payment_safe(payment)

    def _get_reconciled_payments(self):
        self.ensure_one()
        payment_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        reconciled_lines = payment_lines.matched_debit_ids.debit_move_id | payment_lines.matched_credit_ids.credit_move_id
        payments = reconciled_lines.move_id.payment_id
        return payments.filtered(lambda pay: pay.state == 'posted')

    def action_xero_sync(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            if move.state != 'posted':
                move.action_post()
            move.company_id._xero_sync_invoice_safe(move)
            move._xero_sync_reconciled_payments()
        return True

    def action_open_xero_sync_logs(self):
        self.ensure_one()
        return {
            'name': _('Xero Sync Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'xero.sync.log',
            'view_mode': 'tree,form',
            'domain': [
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ],
        }
