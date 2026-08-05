# -*- coding: utf-8 -*-
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_report_lot_names(self):
        """Serial/lot names for customer-facing sale PDFs (empty if none yet)."""
        self.ensure_one()
        if not self.product_id or self.display_type:
            return []
        move_lines = self.move_ids.move_line_ids.filtered(
            lambda ml: ml.state != "cancel" and ml.lot_id
        )
        # Prefer outbound/inbound customer legs; fall back to any assigned lot.
        customer_lines = move_lines.filtered(
            lambda ml: ml.location_dest_id.usage == "customer"
            or ml.location_id.usage == "customer"
        )
        names = (customer_lines or move_lines).mapped("lot_id.name")
        # Preserve order, drop duplicates / blanks.
        return list(dict.fromkeys(n for n in names if n))
