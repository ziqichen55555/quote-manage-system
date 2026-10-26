# -*- coding: utf-8 -*-
"""1.0.214 — Website freight: flat $25 under 1 kg; AusPost PAC at/above 1 kg."""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("quote_manage_ui.shipping_pac_min_kg", "1.0")

    carrier = env.ref(
        "quote_manage_ui.delivery_carrier_rw_au_metro_weight",
        raise_if_not_found=False,
    )
    if carrier:
        carrier.sudo().write(
            {
                "carrier_description": (
                    "Under 1 kg total: $25 ex GST flat. 1 kg and over: "
                    "AusPost by size and weight — shipped to your address."
                ),
            }
        )
    _logger.info("quote_manage_ui 1.0.214: shipping PAC threshold + carrier copy")
