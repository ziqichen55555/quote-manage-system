# -*- coding: utf-8 -*-
from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery
from odoo.exceptions import MissingError
from odoo.http import request

from odoo.addons.quote_manage_ui.website_cart_debug import cart_debug_log


class WebsiteSaleDeliveryReWare(WebsiteSaleDelivery):
    def update_eshop_carrier(self, **post):
        cart_debug_log(
            request.env,
            "route.update_carrier.in",
            carrier_id=post.get("carrier_id"),
        )
        try:
            out = super().update_eshop_carrier(**post)
        except MissingError as err:
            cart_debug_log(
                request.env,
                "route.update_carrier.missing",
                error=str(err),
            )
            so_id = request.session.get("sale_order_id")
            order = (
                request.env["sale.order"].sudo().browse(so_id).exists()
                if so_id
                else request.env["sale.order"]
            )
            if order and post.get("carrier_id"):
                order._quote_website_repair_cart()
                order._check_carrier_quotation(
                    force_carrier_id=int(post["carrier_id"])
                )
                request.website._quote_sync_website_cart_session(order)
                out = self._update_website_sale_delivery_return(order, **post)
            else:
                raise
        cart_debug_log(request.env, "route.update_carrier.out", ok=True)
        return out
