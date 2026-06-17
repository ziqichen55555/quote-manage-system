# -*- coding: utf-8 -*-
import re

from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    rw_rural_mode = fields.Selection(
        [
            ("normal", "Normal"),
            ("metro_only", "Metro only (exclude rural postcodes)"),
            ("rural_only", "Rural only (contact us)"),
        ],
        default="normal",
        string="Rural Mode",
        help="Optional postcode gate for Re-Ware AU shipping policies.",
    )

    def _rw_is_rural_postcode(self, partner):
        self.ensure_one()
        if not partner or partner.country_id.code != "AU":
            return False
        postcode = (partner.zip or "").strip().upper().replace(" ", "")
        if not postcode:
            return False
        icp = self.env["ir.config_parameter"].sudo()
        raw_patterns = icp.get_param("quote_manage_ui.rural_postcode_patterns", default="")
        patterns = [p.strip() for p in re.split(r"[\r\n,;]+", raw_patterns or "") if p.strip()]
        if not patterns:
            return False
        for pattern in patterns:
            if re.match(pattern, postcode):
                return True
        return False

    def _is_available_for_order(self, order):
        available = super()._is_available_for_order(order)
        if not available:
            return False
        self.ensure_one()
        is_rural = self._rw_is_rural_postcode(order.partner_shipping_id)
        if self.rw_rural_mode == "metro_only" and is_rural:
            return False
        if self.rw_rural_mode == "rural_only" and not is_rural:
            return False
        return True
