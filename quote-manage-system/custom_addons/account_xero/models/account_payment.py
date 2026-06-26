# -*- coding: utf-8 -*-

from odoo import _, fields, models

from odoo.addons.account_xero import const
from odoo.addons.account_xero.models.xero_notify import xero_client_notification


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    xero_payment_id = fields.Char(string='Xero Payment ID', copy=False, index=True)
    xero_sync_status = fields.Selection(
        const.SYNC_STATUS_SELECTION,
        string='Xero Sync Status',
        copy=False,
        readonly=True,
    )
    xero_sync_message = fields.Text(string='Xero Sync Message', copy=False, readonly=True)

    def action_post(self):
        super().action_post()
        for payment in self.filtered(lambda p: p.state == 'posted'):
            company = payment.company_id
            if company.xero_enabled and company.xero_connected:
                ok, message = company._xero_sync_payment_safe(payment)
                for invoice in payment.reconciled_invoice_ids.filtered(
                    lambda m: m.move_type == 'out_invoice'
                ):
                    invoice._xero_post_chatter(_('Xero payment'), ok, message)
        return True

    def action_xero_sync(self):
        self.ensure_one()
        if self.state != 'posted':
            self.action_post()
            return xero_client_notification(
                _('Xero payment synced') if self.xero_sync_status == 'synced' else _('Xero payment not synced'),
                self.xero_sync_message or _('Payment posted; see message on linked invoice.'),
                'success' if self.xero_sync_status == 'synced' else 'danger',
            )
        ok, message = self.company_id._xero_sync_payment_safe(self)
        for invoice in self.reconciled_invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice'
        ):
            invoice._xero_post_chatter(_('Xero payment (manual)'), ok, message)
        return xero_client_notification(
            _('Xero payment synced') if ok else _('Xero payment not synced'),
            message,
            'success' if ok else 'danger',
        )
