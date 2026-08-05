# -*- coding: utf-8 -*-
from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_payment_receipt_lot_values(self):
        """Aggregate SN/LN rows from reconciled customer invoices for the receipt PDF."""
        self.ensure_one()
        invoices = self.reconciled_invoice_ids.filtered(
            lambda inv: inv.move_type in ("out_invoice", "out_refund")
        )
        seen = set()
        rows = []
        for inv in invoices:
            for lot in inv._get_invoiced_lot_values():
                key = (lot.get("lot_id"), lot.get("lot_name"), lot.get("product_name"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append(lot)
        return rows
