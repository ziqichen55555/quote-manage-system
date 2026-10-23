# -*- coding: utf-8 -*-
"""Opt-in website cart diagnostics (localhost / troubleshooting)."""
import logging
import os

from odoo.http import request

_logger = logging.getLogger(__name__)

ICP_KEY = "quote_manage_ui.website_cart_debug"


def cart_debug_enabled(env):
    flag = os.environ.get("QUOTE_WEBSITE_CART_DEBUG", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    raw = env["ir.config_parameter"].sudo().get_param(ICP_KEY, "0")
    return raw in ("1", "True", "true", "yes")


def _request_meta():
    path = method = host = ""
    if request and getattr(request, "httprequest", None):
        path = request.httprequest.path or ""
        method = request.httprequest.method or ""
        host = request.httprequest.host or ""
    session = {}
    if request and request.session:
        session = {
            "sale_order_id": request.session.get("sale_order_id"),
            "website_sale_cart_quantity": request.session.get(
                "website_sale_cart_quantity"
            ),
        }
    return {"path": path, "method": method, "host": host, "session": session}


def cart_debug_log(env, event, **extra):
    if not cart_debug_enabled(env):
        return
    user = env.user
    meta = _request_meta()
    _logger.info(
        "[quote cart] %s user=%s(%s) %s extra=%s",
        event,
        user.login,
        user.id,
        meta,
        extra,
    )


def _line_row(line):
    return {
        "id": line.id,
        "product_id": line.product_id.id,
        "product": (line.product_id.display_name or "")[:120],
        "qty": line.product_uom_qty,
        "is_delivery": bool(line.is_delivery),
        "display_type": line.display_type or False,
    }


def sale_order_cart_debug_dict(order):
    """Safe snapshot: DB lines vs cached order_line vs website_order_line."""
    if not order or not order.exists():
        return {"order": None}
    order = order.sudo()
    db_lines = order.env["sale.order.line"].search([("order_id", "=", order.id)])
    db_ids = set(db_lines.ids)
    cached_ids = set(order.order_line.ids)
    stale_ids = sorted(cached_ids - db_ids)
    ghost_exists = []
    for lid in stale_ids:
        ghost_exists.append({"id": lid, "exists": bool(order.env["sale.order.line"].browse(lid).exists())})
    try:
        website_lines = order.website_order_line
        website_rows = [_line_row(l) for l in website_lines]
        cart_qty = order.cart_quantity
    except Exception as exc:
        website_rows = []
        cart_qty = f"compute_error: {exc!r}"
    return {
        "order_id": order.id,
        "name": order.name,
        "state": order.state,
        "website_id": order.website_id.id if order.website_id else None,
        "partner_id": order.partner_id.id,
        "carrier_id": order.carrier_id.id if order.carrier_id else None,
        "cart_quantity": cart_qty,
        "db_line_ids": sorted(db_ids),
        "cached_order_line_ids": sorted(cached_ids),
        "stale_cached_line_ids": stale_ids,
        "stale_line_exists_check": ghost_exists,
        "db_lines": [_line_row(l) for l in db_lines],
        "website_order_lines": website_rows,
    }


def build_cart_debug_payload(env):
    meta = _request_meta()
    order = None
    if request and request.website:
        order = request.website.sale_get_order()
    payload = {
        "debug_enabled": True,
        "icp_key": ICP_KEY,
        "request": meta,
        "cart": sale_order_cart_debug_dict(order),
    }
    if order and order.exists() and order.partner_id:
        payload["partner"] = {
            "id": order.partner_id.id,
            "name": order.partner_id.name,
            "last_website_so_id": order.partner_id.last_website_so_id.id
            if order.partner_id.last_website_so_id
            else None,
        }
    return payload
