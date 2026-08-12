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

    def action_xero_sync(self):
        """Payments are intentionally not pushed to Xero."""
        self.ensure_one()
        message = _(
            'Payment sync to Xero is disabled. Register payment method and status in '
            'Odoo as usual; only the invoice is pushed to Xero.'
        )
        self.sudo().write({
            'xero_sync_status': 'skipped',
            'xero_sync_message': message,
        })
        return xero_client_notification(
            _('Xero payment not synced'),
            message,
            'warning',
        )
