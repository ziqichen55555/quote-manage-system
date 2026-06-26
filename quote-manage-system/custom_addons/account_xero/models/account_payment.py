# -*- coding: utf-8 -*-

from odoo import fields, models

from odoo.addons.account_xero import const


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
        for payment in self:
            company = payment.company_id
            if company.xero_enabled and company.xero_connected:
                company._xero_sync_payment_safe(payment)

    def action_xero_sync(self):
        for payment in self:
            if payment.state != 'posted':
                payment.action_post()
            else:
                payment.company_id._xero_sync_payment_safe(payment)
        return True
