# -*- coding: utf-8 -*-
from odoo import api, models


class QuoteManageUiSetup(models.AbstractModel):
    _name = "quote.manage.ui.setup"
    _description = "One-shot setup helpers for quote_manage_ui"

    @api.model
    def enable_lots_and_serial_numbers(self):
        """Turn on Inventory › Lots & Serial Numbers (stock.group_production_lot)."""
        group = self.env.ref("stock.group_production_lot", raise_if_not_found=False)
        if not group:
            return False
        user_group = self.env.ref("base.group_user")
        if group in user_group.implied_ids:
            return True
        self.env["res.config.settings"].sudo().create(
            {"group_stock_production_lot": True}
        ).execute()
        return True
