# -*- coding: utf-8 -*-
"""1.0.177 — Fixed $25 ex GST freight; unify shipping product + carrier."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env["ir.config_parameter"].sudo()
    ICP.set_param("quote_manage_ui.default_freight_price", "25.0")

    metro = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
        raise_if_not_found=False,
    )
    rural = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_rural_quote",
        raise_if_not_found=False,
    )
    ship_prod = env.ref(
        "quote_manage_ui.product_product_shipping_metro_weight",
        raise_if_not_found=False,
    )
    rural_prod = env.ref(
        "quote_manage_ui.product_product_shipping_rural_quote",
        raise_if_not_found=False,
    )

    freight_vals = {
        "list_price": 25.0,
        "standard_price": 25.0,
    }
    if ship_prod:
        ship_prod.write({
            **freight_vals,
            "name": "Shipping - Standard",
            "default_code": "RW_SHIP_STANDARD",
        })
        ship_prod.product_tmpl_id.write(freight_vals)
    if rural_prod:
        rural_prod.write(freight_vals)
        rural_prod.product_tmpl_id.write(freight_vals)

    if metro:
        metro.write({
            "delivery_type": "fixed",
            "fixed_price": 25.0,
            "rw_rural_mode": "normal",
            "website_published": True,
            "carrier_description": "Standard shipping: $25 ex GST (fixed).",
        })
        # Remove old weight-based price rules if any remain.
        metro.price_rule_ids.unlink()
    if rural:
        rural.write({
            "fixed_price": 25.0,
            "website_published": False,
        })
