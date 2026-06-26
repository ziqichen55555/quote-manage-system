# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        res = super().reconcile()
        invoices = self.mapped('move_id').filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
        )
        for invoice in invoices:
            company = invoice.company_id
            if not company.xero_enabled or not company.xero_connected:
                continue
            if not invoice.xero_invoice_id:
                company._xero_sync_invoice_safe(invoice)
            invoice._xero_sync_reconciled_payments()
        return res
