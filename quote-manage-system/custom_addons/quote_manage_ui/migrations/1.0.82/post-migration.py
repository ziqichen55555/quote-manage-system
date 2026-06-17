# -*- coding: utf-8 -*-
"""1.0.82 — Backend wizard: Upload inventory CSV with Series merge."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Ensure Configuration attribute exists on DBs that already loaded attributes with noupdate.
    Attr = env["product.attribute"].sudo()
    if not Attr.search([("name", "=", "Configuration")], limit=1):
        Attr.create(
            {
                "name": "Configuration",
                "create_variant": "always",
                "display_type": "select",
            }
        )
