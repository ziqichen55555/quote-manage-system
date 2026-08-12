# -*- coding: utf-8 -*-
"""1.0.177 — Fixed $25 freight; staff notify emails; Chris on appointment + Sales team."""

from odoo import SUPERUSER_ID, api

_STAFF_NOTIFY_EMAILS = (
    "louismoncrieff@cocreativeit.com",
    "drewwright@cocreativeit.com",
    "chrischen@cocreativeit.com",
)
_TEAM_LOGINS = (
    "re-ware@cocreativeit.com",
    "louismoncrieff@cocreativeit.com",
    "drewwright@cocreativeit.com",
    "chrischen@cocreativeit.com",
)
_TEAM_PARAM = "quote_manage_ui.appointment_team_user_ids"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env["ir.config_parameter"].sudo()
    Users = env["res.users"].sudo()

    ICP.set_param("quote_manage_ui.default_freight_price", "25.0")
    ICP.set_param(
        "quote_manage_ui.website_order_notify_email",
        ", ".join(_STAFF_NOTIFY_EMAILS),
    )

    team_users = Users.search([
        ("login", "in", list(_TEAM_LOGINS)),
        ("share", "=", False),
        ("active", "=", True),
    ])
    mandatory_ids = set(team_users.ids)
    raw = ICP.get_param(_TEAM_PARAM, "") or ""
    configured_ids = {int(uid) for uid in raw.split(",") if uid.strip().isdigit()}
    merged_ids = sorted(configured_ids | mandatory_ids)
    if merged_ids:
        ICP.set_param(_TEAM_PARAM, ",".join(str(uid) for uid in merged_ids))

    sales_team = env["crm.team"].sudo().search([("name", "=", "Sales")], limit=1)
    staff_three = Users.search([
        ("login", "in", list(_STAFF_NOTIFY_EMAILS)),
        ("share", "=", False),
        ("active", "=", True),
    ])
    if sales_team and staff_three:
        sales_team.write({"member_ids": [(4, uid) for uid in staff_three.ids]})

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
