# -*- coding: utf-8 -*-
import math

from odoo import _, api, fields, models
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.http import request

from odoo.addons.quote_manage_ui.website_cart_debug import cart_debug_log


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

    def _quote_billing_mandatory_field_names(self, partner):
        """Match website checkout billing rules (+ phone on Re-Ware shop)."""
        country = partner.country_id
        names = [
            "name",
            "email",
            "street",
            "city",
            "zip",
            "country_id",
            "phone",
        ]
        if country and country.state_required:
            names.append("state_id")
        return names

    def _quote_partner_has_complete_billing(self, partner):
        if not partner:
            return False
        for fname in self._quote_billing_mandatory_field_names(partner):
            if fname == "phone":
                if not (partner.phone or partner.mobile or "").strip():
                    return False
            elif fname in ("country_id", "state_id"):
                if not partner[fname]:
                    return False
            else:
                if not (partner[fname] or "").strip():
                    return False
        return True

    def _quote_has_contactable_customer(self):
        """Real customer (not Public User) with billing contact + address."""
        self.ensure_one()
        if not self.website_id:
            return True
        partner = self.partner_id
        public_partner = self.website_id.user_id.partner_id
        if not partner or partner == public_partner:
            return False
        return self._quote_partner_has_complete_billing(partner)

    @api.depends("company_id", "website_id")
    def _compute_require_payment(self):
        """Website quotations become Sales Orders only after payment."""
        super()._compute_require_payment()
        for order in self.filtered("website_id"):
            order.require_payment = True

    def _check_cart_is_ready_to_be_paid(self):
        self._rw_ensure_default_freight()
        super()._check_cart_is_ready_to_be_paid()
        if self.website_id and not self._quote_has_contactable_customer():
            raise ValidationError(
                _(
                    "Please complete your name, email, phone and billing address "
                    "before placing a quotation or paying."
                )
            )
        self.filtered(
            lambda o: o.website_id and o.state in ("draft", "sent")
        )._send_website_quotation_staff_notification()

    def write(self, vals):
        res = super().write(vals)
        if "carrier_id" in vals:
            self._rw_ensure_default_freight()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._rw_ensure_default_freight()
        return orders

    def _rw_default_freight_price(self):
        """AUD ex GST per billable kg (by post). System param default 25.0."""
        icp = self.env["ir.config_parameter"].sudo()
        raw = icp.get_param("quote_manage_ui.default_freight_price", "25.0")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 25.0

    def _rw_shipping_weight_kg(self):
        """Sum qty×weight; any line without weight adds 1 kg once (whole order)."""
        self.ensure_one()
        total = 0.0
        missing_weight = False
        for line in self._rw_freight_product_lines():
            weight = line.product_id.weight or 0.0
            if weight <= 0:
                missing_weight = True
            else:
                total += line.product_uom_qty * weight
        if missing_weight:
            total += 1.0
        return total

    def _rw_freight_billable_kg(self):
        """Ceiling total kg, minimum 1 kg."""
        self.ensure_one()
        return max(1, math.ceil(self._rw_shipping_weight_kg()))

    def _rw_freight_price_ex_gst(self):
        """By post: ceil(kg)×rate ex GST, min 1 kg. Pickup callers use 0 separately."""
        self.ensure_one()
        return self._rw_freight_billable_kg() * self._rw_default_freight_price()

    def _rw_get_post_carrier(self):
        return self.env.ref(
            "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
            raise_if_not_found=False,
        )

    def _rw_get_pickup_carrier(self):
        return self.env.ref(
            "quote_manage_ui.delivery_carrier_rw_pickup_store",
            raise_if_not_found=False,
        )

    def _rw_is_pickup_carrier(self, carrier):
        pickup = self._rw_get_pickup_carrier()
        return bool(pickup and carrier and carrier.id == pickup.id)

    def rw_delivery_method_label(self):
        """Customer-facing: By post | In-store pickup."""
        self.ensure_one()
        if self._rw_is_pickup_carrier(self.carrier_id):
            return _("In-store pickup")
        return _("By post")

    def _quote_db_order_lines(self):
        """Fresh lines from DB (website carts: avoid stale deleted ids in cache)."""
        self.ensure_one()
        return self.env["sale.order.line"].sudo().search([("order_id", "=", self.id)])

    def _quote_order_lines_for_ops(self):
        self.ensure_one()
        if self.website_id:
            return self._quote_db_order_lines()
        return self.order_line.exists()

    def _compute_website_order_line(self):
        for order in self:
            lines = order._quote_order_lines_for_ops()
            order.website_order_line = lines.filtered(lambda line: line._show_in_cart())

    def _quote_website_product_cart_lines(self):
        """Non-delivery lines stored on the SO (DB read for website carts)."""
        self.ensure_one()
        return self._quote_db_order_lines().filtered(
            lambda line: not line.is_delivery
            and not line.display_type
            and line.product_id
        )

    @api.depends("order_line.product_uom_qty", "order_line.product_id")
    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self.filtered("website_id"):
            if order.cart_quantity:
                continue
            product_lines = order._quote_website_product_cart_lines()
            if not product_lines:
                continue
            order.cart_quantity = int(
                sum(product_lines.mapped("product_uom_qty"))
            )
            order.only_services = all(
                line.product_id.type == "service" for line in product_lines
            )

    def _rw_freight_product_lines(self):
        self.ensure_one()
        return self._quote_order_lines_for_ops().filtered(
            lambda l: not l.display_type
            and not l.is_delivery
            and l.product_id
            and l.product_id.type != "service"
        )

    def _rw_should_apply_freight(self):
        self.ensure_one()
        if self.state in ("cancel", "done"):
            return False
        if not self._rw_freight_product_lines():
            return False
        if self.only_services:
            return False
        return True

    def _get_delivery_methods(self):
        carriers = super()._get_delivery_methods()
        if not self.website_id:
            return carriers
        post = self._rw_get_post_carrier()
        pickup = self._rw_get_pickup_carrier()
        allowed = (post | pickup).exists()
        if not allowed:
            return carriers
        return carriers.filtered(lambda c: c in allowed)

    def _rw_ensure_default_freight(self):
        """By post: weight-based freight. In-store pickup: $0."""
        if self.env.context.get("rw_skip_default_freight"):
            return
        post = self._rw_get_post_carrier()
        pickup = self._rw_get_pickup_carrier()
        for order in self:
            if not order._rw_should_apply_freight():
                continue
            order_ctx = order.with_context(rw_skip_default_freight=True)
            carrier = order_ctx.carrier_id
            if order_ctx._rw_is_pickup_carrier(carrier):
                target = pickup
                price = 0.0
            else:
                target = post
                price = order_ctx._rw_freight_price_ex_gst()
            if not target:
                continue
            order_ctx.carrier_id = target
            order_ctx.with_context(
                rw_force_delivery_remove=True,
            )._remove_delivery_line()
            order_ctx.with_context(
                rw_force_delivery_remove=True,
            ).set_delivery_line(target, price)
            order_ctx.delivery_rating_success = True
            order.invalidate_recordset(
                ["website_order_line", "cart_quantity", "only_services"]
            )

    def _get_confirmation_template(self):
        self.ensure_one()
        template = super()._get_confirmation_template()
        if self.website_id:
            custom = self.env.ref(
                "quote_manage_ui.mail_template_sale_confirmation_reware",
                raise_if_not_found=False,
            )
            if custom:
                return custom
        return template

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

    def _quote_website_repair_cart(self):
        """Drop deleted line ids from cache (backend edits / stale website session)."""
        self.ensure_one()
        if self.env.context.get("rw_repairing_cart"):
            return
        self = self.with_context(rw_repairing_cart=True)
        db_line_ids = set(
            self.env["sale.order.line"]
            .sudo()
            .search([("order_id", "=", self.id)])
            .ids
        )
        cached_ids = set(self.order_line.ids)
        stale = cached_ids - db_line_ids
        if stale:
            self.invalidate_recordset(["order_line"])
            cart_debug_log(
                self.env,
                "repair_cart.stale_cache",
                order_id=self.id,
                stale_cached_line_ids=sorted(stale),
                db_line_ids=sorted(db_line_ids),
            )
        delivery_count = self.env["sale.order.line"].sudo().search_count(
            [("order_id", "=", self.id), ("is_delivery", "=", True)]
        )
        if (
            delivery_count > 1
            and not self.env.context.get("rw_consolidating_delivery")
        ):
            cart_debug_log(
                self.env,
                "repair_cart.duplicate_delivery",
                order_id=self.id,
                delivery_count=delivery_count,
            )
            self.env["sale.order.line"].sudo().search(
                [("order_id", "=", self.id), ("is_delivery", "=", True)]
            ).with_context(rw_skip_default_freight=True).unlink()
            self.with_context(
                rw_consolidating_delivery=True,
            )._rw_ensure_default_freight()
        self.order_line.exists()

    def _remove_delivery_line(self):
        # website_sale.cart() strips delivery when carrier_id is set; Re-Ware weight
        # freight re-adds on line unlink → MissingError → session cleared.
        if not self.env.context.get("rw_force_delivery_remove"):
            if self.env.context.get("rw_in_cart_update"):
                cart_debug_log(
                    self.env,
                    "remove_delivery_line.skipped",
                    reason="rw_in_cart_update",
                    order_ids=self.ids,
                )
                return
            if request and getattr(request, "httprequest", None):
                path = (
                    (request.httprequest.path or "").split("?", 1)[0].rstrip("/")
                    or "/"
                )
                # Skip on all /shop/cart* routes: Odoo _cart_update calls remove before qty
                # change; Re-Ware refreshes shipping via _rw_ensure_default_freight instead.
                if path == "/shop/cart" or path.startswith("/shop/cart/"):
                    cart_debug_log(
                        self.env,
                        "remove_delivery_line.skipped",
                        path=request.httprequest.path,
                        order_ids=self.ids,
                    )
                    return
        delivery_lines = self.env["sale.order.line"].sudo().search(
            [("order_id", "in", self.ids), ("is_delivery", "=", True)]
        )
        if not delivery_lines:
            return
        to_delete = delivery_lines.filtered(lambda line: line.qty_invoiced == 0)
        if not to_delete:
            raise UserError(
                _(
                    "You can not update the shipping costs on an order where it was "
                    "already invoiced!\n\nThe following delivery lines (product, "
                    "invoiced quantity and price) have already been processed:\n\n"
                )
                + "\n".join(
                    [
                        "- %s: %s x %s"
                        % (
                            line.product_id.with_context(
                                display_default_code=False
                            ).display_name,
                            line.qty_invoiced,
                            line.price_unit,
                        )
                        for line in delivery_lines
                    ]
                )
            )
        cart_debug_log(
            self.env,
            "remove_delivery_line",
            order_ids=self.ids,
            delivery_line_ids=delivery_lines.ids,
            unlink_ids=to_delete.ids,
        )
        to_delete.unlink()

    def _quote_resolve_cart_line_id(self, product_id, line_id=None):
        """Map stale website line_id to a live product line on this order."""
        self.ensure_one()
        product_id = int(product_id)
        if line_id is not False and line_id is not None:
            line = self.env["sale.order.line"].sudo().browse(int(line_id))
            if (
                line.exists()
                and line.order_id == self
                and not line.is_delivery
                and line.product_id.id == product_id
            ):
                return line.id
        lines = self._quote_website_product_cart_lines().filtered(
            lambda l: l.product_id.id == product_id
        )
        return lines[:1].id if lines else None

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        line_id = self._quote_resolve_cart_line_id(product_id, line_id=line_id)
        if line_id is False:
            return self.env["sale.order.line"]
        return super()._cart_find_product_line(
            product_id, line_id=line_id, **kwargs
        )

    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        self._quote_website_repair_cart()
        line_id = self._quote_resolve_cart_line_id(product_id, line_id=line_id)
        cart_debug_log(
            self.env,
            "cart_update.in",
            order_id=self.id,
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
        )
        order = self.with_context(rw_in_cart_update=True)
        try:
            out = super(SaleOrder, order)._cart_update(
                product_id,
                line_id=line_id,
                add_qty=add_qty,
                set_qty=set_qty,
                **kwargs,
            )
        except MissingError as err:
            cart_debug_log(
                self.env,
                "cart_update.missing_retry",
                order_id=self.id,
                error=str(err),
            )
            order._quote_website_repair_cart()
            line_id = order._quote_resolve_cart_line_id(product_id, line_id=None)
            out = super(SaleOrder, order)._cart_update(
                product_id,
                line_id=line_id,
                add_qty=add_qty,
                set_qty=set_qty,
                **kwargs,
            )
        if order.website_id:
            order._rw_ensure_default_freight()
            order.invalidate_recordset(
                ["order_line", "website_order_line", "cart_quantity"]
            )
            resolved = order._quote_resolve_cart_line_id(
                product_id, line_id=out.get("line_id")
            )
            if resolved:
                out["line_id"] = resolved
        cart_debug_log(
            self.env,
            "cart_update.out",
            order_id=self.id,
            line_id=out.get("line_id"),
            quantity=out.get("quantity"),
        )
        return out

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
        if not self.env.context.get("rw_in_cart_update"):
            lines.order_id._rw_ensure_default_freight()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get("rw_in_cart_update")
            and {"product_id", "product_uom_qty"} & set(vals)
        ):
            self.order_id._rw_ensure_default_freight()
        return res

    def unlink(self):
        self = self.exists()
        if not self:
            return True
        orders = self.order_id
        only_delivery = all(line.is_delivery for line in self)
        res = super().unlink()
        if (
            not only_delivery
            and not self.env.context.get("rw_skip_default_freight")
            and not self.env.context.get("rw_in_cart_update")
        ):
            orders._rw_ensure_default_freight()
        return res

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
