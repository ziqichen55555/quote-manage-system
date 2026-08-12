# -*- coding: utf-8 -*-

from odoo import _, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        res = super().reconcile()
        # Ensure the customer invoice exists in Xero after payment reconciliation.
        # Do not push payment status/method to Xero — that stays in Odoo only.
        invoices = self.mapped('move_id').filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
        )
        for invoice in invoices:
            company = invoice.company_id
            if not company.xero_enabled or not company.sudo().xero_connected:
                continue
            if invoice.xero_invoice_id:
                continue
            ok, message = company.sudo()._xero_sync_invoice_safe(invoice)
            invoice._xero_post_chatter(_('Xero invoice'), ok, message)
        return res
