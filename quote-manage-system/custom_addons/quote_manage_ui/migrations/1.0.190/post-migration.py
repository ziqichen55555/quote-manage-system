# -*- coding: utf-8 -*-
"""1.0.190 — Weight-based metro freight ($25/kg ceil, min 1 kg); hide Odoo demo carrier."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    metro = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
        raise_if_not_found=False,
    )
    if metro:
        metro.write({
            "delivery_type": "fixed",
            "fixed_price": 25.0,
            "website_published": True,
            "carrier_description": (
                "Standard shipping: $25 ex GST per kg (rounded up, minimum 1 kg)."
            ),
        })
        metro.price_rule_ids.unlink()

    demo = env.ref("delivery.free_delivery_carrier", raise_if_not_found=False)
    if demo:
        demo.write({
            "website_published": False,
            "delivery_type": "fixed",
            "fixed_price": 0.0,
        })
        demo.price_rule_ids.unlink()

    env.registry.clear_cache()
