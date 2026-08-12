# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    quote_is_anonymous_website_cart = fields.Boolean(
        string="Anonymous Website Cart",
        compute="_compute_quote_is_anonymous_website_cart",
        store=True,
        index=True,
        help="Website cart still assigned to the Public User partner "
        "(customer has not submitted contact details yet).",
    )

    @api.depends("partner_id", "website_id", "website_id.user_id", "website_id.user_id.partner_id")
    def _compute_quote_is_anonymous_website_cart(self):
        for order in self:
            public_partner = (
                order.website_id.user_id.partner_id if order.website_id else False
            )
            order.quote_is_anonymous_website_cart = bool(
                public_partner and order.partner_id == public_partner
            )

    def _quote_has_contactable_customer(self):
        """Real customer details required before a website cart is a quotation."""
        self.ensure_one()
        partner = self.partner_id
        return bool(
            partner
            and not self.quote_is_anonymous_website_cart
            and (partner.name or "").strip()
            and (partner.email or "").strip()
            and (partner.phone or partner.mobile or "").strip()
        )

    @api.depends("company_id", "website_id")
    def _compute_require_payment(self):
        """Website quotations confirm to SO only after payment."""
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
                    "Please provide your name, email and phone before placing "
                    "this quotation or proceeding to payment."
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
        # Prefer outbound/inbound customer legs; fall back to any assigned lot.
        customer_lines = move_lines.filtered(
            lambda ml: ml.location_dest_id.usage == "customer"
            or ml.location_id.usage == "customer"
        )
        names = (customer_lines or move_lines).mapped("lot_id.name")
        # Preserve order, drop duplicates / blanks.
        return list(dict.fromkeys(n for n in names if n))
