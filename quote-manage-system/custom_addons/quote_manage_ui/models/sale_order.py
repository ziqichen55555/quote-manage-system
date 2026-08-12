# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _quote_has_contactable_customer(self):
        """Account partner must have name, email and phone (no Public User)."""
        self.ensure_one()
        if not self.website_id:
            return True
        partner = self.partner_id
        public_partner = self.website_id.user_id.partner_id
        if not partner or partner == public_partner:
            return False
        return bool(
            (partner.name or "").strip()
            and (partner.email or "").strip()
            and (partner.phone or partner.mobile or "").strip()
        )

    @api.depends("company_id", "website_id")
    def _compute_require_payment(self):
        """Website quotations become Sales Orders only after payment."""
        super()._compute_require_payment()
        for order in self.filtered("website_id"):
            order.require_payment = True

    def _is_cart_ready(self):
        ready = super()._is_cart_ready()
        if not ready:
            return False
        if self.website_id and not self._quote_has_contactable_customer():
            return False
        return True

    def _check_cart_is_ready_to_be_paid(self):
        super()._check_cart_is_ready_to_be_paid()
        if self.website_id and not self._quote_has_contactable_customer():
            raise ValidationError(
                _(
                    "Please sign in or create an account with your name, email "
                    "and phone before placing a quotation or paying."
                )
            )


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
        customer_lines = move_lines.filtered(
            lambda ml: ml.location_dest_id.usage == "customer"
            or ml.location_id.usage == "customer"
        )
        names = (customer_lines or move_lines).mapped("lot_id.name")
        return list(dict.fromkeys(n for n in names if n))
