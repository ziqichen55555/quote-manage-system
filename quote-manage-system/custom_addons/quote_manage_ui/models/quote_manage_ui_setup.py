# -*- coding: utf-8 -*-
from odoo import api, models


class QuoteManageUiSetup(models.AbstractModel):
    _name = "quote.manage.ui.setup"
    _description = "One-shot setup helpers for quote_manage_ui"

    @api.model
    def enable_lots_and_serial_numbers(self):
        """Turn on Lots & Serial Numbers + show them on invoices (and delivery slips)."""
        group = self.env.ref("stock.group_production_lot", raise_if_not_found=False)
        if not group:
            return False

        settings_vals = {"group_stock_production_lot": True}
        # Invoice SN/LN table (stock_account).
        if self.env["ir.model.fields"].sudo().search_count([
            ("model", "=", "res.config.settings"),
            ("name", "=", "group_lot_on_invoice"),
        ]):
            settings_vals["group_lot_on_invoice"] = True
        # Delivery slip SN column (stock).
        if self.env["ir.model.fields"].sudo().search_count([
            ("model", "=", "res.config.settings"),
            ("name", "=", "group_lot_on_delivery_slip"),
        ]):
            settings_vals["group_lot_on_delivery_slip"] = True

        user_group = self.env.ref("base.group_user")
        lot_on_invoice = self.env.ref(
            "stock_account.group_lot_on_invoice", raise_if_not_found=False
        )
        lot_on_delivery = self.env.ref(
            "stock.group_lot_on_delivery_slip", raise_if_not_found=False
        )
        already = (
            group in user_group.implied_ids
            and (not lot_on_invoice or lot_on_invoice in user_group.implied_ids)
            and (not lot_on_delivery or lot_on_delivery in user_group.implied_ids)
        )
        if already:
            return True

        self.env["res.config.settings"].sudo().create(settings_vals).execute()
        return True
