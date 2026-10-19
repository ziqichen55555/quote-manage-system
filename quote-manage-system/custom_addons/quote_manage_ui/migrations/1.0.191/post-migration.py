# -*- coding: utf-8 -*-
"""1.0.191 — Flat $25/order post + in-store pickup; hide Odoo demo carrier."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    post = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
        raise_if_not_found=False,
    )
    pickup = env.ref(
        "quote_manage_ui.delivery_carrier_rw_pickup_store",
        raise_if_not_found=False,
    )
    if post:
        post.write({
            "name": "Standard shipping (by post)",
            "delivery_type": "fixed",
            "fixed_price": 25.0,
            "website_published": True,
            "rw_store_pickup": False,
            "carrier_description": (
                "Flat $25 ex GST per order — we ship to your address."
            ),
        })
        post.price_rule_ids.unlink()
    if pickup:
        pickup.write({
            "website_published": True,
            "fixed_price": 0.0,
            "rw_store_pickup": True,
        })
    rural = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_rural_quote",
        raise_if_not_found=False,
    )
    if rural:
        rural.write({"website_published": False})
    demo = env.ref("delivery.free_delivery_carrier", raise_if_not_found=False)
    if demo:
        demo.write({
            "website_published": False,
            "delivery_type": "fixed",
            "fixed_price": 0.0,
        })
        demo.price_rule_ids.unlink()
    env.registry.clear_cache()
