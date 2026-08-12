# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    rw_website_quotation_staff_notified = fields.Boolean(
        copy=False,
        readonly=True,
        help="Staff notified: unpaid website quotation at checkout (do not confirm).",
    )
    rw_website_sale_staff_notified = fields.Boolean(
        copy=False,
        readonly=True,
        help="Staff notified: paid website order confirmed.",
    )

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
        self._rw_ensure_default_freight()
        super()._check_cart_is_ready_to_be_paid()
        self.filtered(
            lambda o: o.website_id and o.state in ("draft", "sent")
        )._send_website_quotation_staff_notification()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._rw_ensure_default_freight()
        return orders

    def _rw_default_freight_price(self):
        icp = self.env["ir.config_parameter"].sudo()
        raw = icp.get_param("quote_manage_ui.default_freight_price", "25.0")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 25.0

    def _rw_get_default_carrier(self):
        return self.env.ref(
            "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
            raise_if_not_found=False,
        )

    def _rw_needs_freight_line(self):
        self.ensure_one()
        if self.state in ("cancel", "done"):
            return False
        if self.order_line.filtered("is_delivery"):
            return False
        product_lines = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_delivery
        )
        if not product_lines:
            return False
        if self.only_services:
            return False
        return True

    def _rw_ensure_default_freight(self):
        """Add fixed $25 ex GST shipping line when missing (editable by staff)."""
        if self.env.context.get("rw_skip_default_freight"):
            return
        carrier = self._rw_get_default_carrier()
        price = self._rw_default_freight_price()
        for order in self:
            if not order._rw_needs_freight_line():
                continue
            order_ctx = order.with_context(rw_skip_default_freight=True)
            if carrier:
                order_ctx.carrier_id = carrier
                if carrier.delivery_type == "fixed":
                    order_ctx._remove_delivery_line()
                    order_ctx.set_delivery_line(carrier, price)
                    order_ctx.delivery_rating_success = True
                else:
                    order_ctx._check_carrier_quotation(force_carrier_id=carrier.id)

    def _send_website_quotation_staff_notification(self):
        template = self.env.ref(
            "quote_manage_ui.mail_template_website_quotation_staff",
            raise_if_not_found=False,
        )
        if not template:
            return
        for order in self:
            if order.rw_website_quotation_staff_notified or order.state == "sale":
                continue
            template.send_mail(order.id, force_send=True)
            order.write({"rw_website_quotation_staff_notified": True})

    def _action_confirm(self):
        res = super()._action_confirm()
        self.filtered(
            lambda o: o.website_id and not o.rw_website_sale_staff_notified
        )._send_website_sale_staff_notification()
        return res

    def _send_website_sale_staff_notification(self):
        template = self.env.ref(
            "quote_manage_ui.mail_template_website_order_staff",
            raise_if_not_found=False,
        )
        if not template:
            return
        for order in self:
            if order.rw_website_sale_staff_notified:
                continue
            template.send_mail(order.id, force_send=True)
            order.write({"rw_website_sale_staff_notified": True})


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.order_id._rw_ensure_default_freight()
        return lines

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
