# -*- coding: utf-8 -*-

from odoo import _, fields, models

from odoo.addons.account_xero import const
from odoo.addons.account_xero.models.xero_notify import xero_client_notification


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
            if not company.xero_enabled or not company.xero_connected:
                continue
            ok, message = company._xero_sync_invoice_safe(move)
            move._xero_post_chatter(_('Xero invoice'), ok, message)
            pay_ok, pay_message = move._xero_sync_reconciled_payments()
            if pay_message:
                move._xero_post_chatter(_('Xero payment'), pay_ok, pay_message)
        return posted

    def _xero_post_chatter(self, label, success, message):
        self.ensure_one()
        if not message:
            return
        icon = '✅' if success else '❌'
        self.message_post(
            body=f'<p><strong>{label}</strong> {icon}<br/>{message}</p>',
            subtype_xmlid='mail.mt_note',
        )

    def _xero_sync_reconciled_payments(self):
        """Returns (all_ok, combined_message)."""
        self.ensure_one()
        payments = self._get_reconciled_payments()
        if not payments:
            return True, ''
        results = []
        all_ok = True
        for payment in payments:
            ok, message = self.company_id._xero_sync_payment_safe(payment)
            if not ok:
                all_ok = False
            if message:
                results.append(f'{payment.display_name}: {message}')
        return all_ok, '\n'.join(results)

    def _get_reconciled_payments(self):
        self.ensure_one()
        payment_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        reconciled_lines = payment_lines.matched_debit_ids.debit_move_id | payment_lines.matched_credit_ids.credit_move_id
        payments = reconciled_lines.move_id.payment_id
        return payments.filtered(lambda pay: pay.state == 'posted')

    def action_xero_sync(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return xero_client_notification(
                _('Xero'),
                _('Only customer invoices can be synced to Xero.'),
                'warning',
            )
        if self.state != 'posted':
            self.action_post()
        ok, message = self.company_id._xero_sync_invoice_safe(self)
        self._xero_post_chatter(_('Xero invoice (manual)'), ok, message)
        pay_ok, pay_message = self._xero_sync_reconciled_payments()
        if pay_message:
            self._xero_post_chatter(_('Xero payment (manual)'), pay_ok, pay_message)
            if not pay_ok:
                message = f'{message}\n\n{pay_message}' if message else pay_message
                ok = ok and pay_ok
        return xero_client_notification(
            _('Xero sync succeeded') if ok else _('Xero sync failed'),
            message,
            'success' if ok else 'danger',
        )

    def action_xero_sync_payments(self):
        self.ensure_one()
        if self.move_type != 'out_invoice' or self.state != 'posted':
            return xero_client_notification(
                _('Xero'),
                _('Post the customer invoice before syncing payments.'),
                'warning',
            )
        if not self.xero_invoice_id:
            return xero_client_notification(
                _('Xero'),
                _('Sync the invoice to Xero first (Push to Xero).'),
                'warning',
            )
        ok, message = self._xero_sync_reconciled_payments()
        if not message:
            message = _('No posted customer payment is linked to this invoice yet.')
            ok = False
        self._xero_post_chatter(_('Xero payment (manual)'), ok, message)
        return xero_client_notification(
            _('Xero payment synced') if ok else _('Xero payment not synced'),
            message,
            'success' if ok else 'danger',
        )

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
