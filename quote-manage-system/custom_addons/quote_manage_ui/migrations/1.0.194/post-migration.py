# -*- coding: utf-8 -*-
"""1.0.194 — By-post freight: ceil(kg)×$25 ex GST, min 1 kg; pickup stays $0."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    post = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
        raise_if_not_found=False,
    )
    if post:
        post.write({
            "carrier_description": (
                "$25 ex GST per kg (rounded up, minimum 1 kg) — shipped to your address."
            ),
        })
    env.registry.clear_cache()
