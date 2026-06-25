# -*- coding: utf-8 -*-
"""1.0.122: purge auto S/N placeholder stock on refurb laptops/desktops."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    imp = env["product.csv.importer"]
    cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
    cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
    for tmpl in env["product.template"].sudo().search(
        [
            ("type", "=", "product"),
            ("public_categ_ids", "in", [cat_l, cat_d]),
            ("default_code", "!=", False),
        ]
    ):
        imp.purge_auto_generated_serial_stock(tmpl.default_code)
