# -*- coding: utf-8 -*-
"""1.0.114 — Shop categories: drop Computer Systems duplicate, reorder, stock counts, hero RRR."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Category = env["product.public.category"]
    if hasattr(Category, "repair_shop_public_categories"):
        Category.repair_shop_public_categories()

    View = env["ir.ui.view"]
    if hasattr(View, "_quote_manage_ui_sync_single_template_from_xml"):
        for key in ("rw_footer_block", "s_rw_categories"):
            try:
                View._quote_manage_ui_sync_single_template_from_xml(key)
            except Exception:
                pass

    cr.commit()
