# -*- coding: utf-8 -*-
"""1.0.228 — SEO landing pages, homepage hero/H1, head metadata, snippet sync."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Page = env["website.page"]
    View = env["ir.ui.view"]
    Product = env["product.template"]

    if hasattr(Page, "_quote_manage_ui_apply_seo_metadata"):
        Page._quote_manage_ui_apply_seo_metadata()
    if hasattr(Page, "_quote_manage_ui_ensure_google_indexable"):
        Page._quote_manage_ui_ensure_google_indexable()

    for key in (
        "s_rw_hero",
        "s_rw_services",
        "rw_footer_block",
        "template_header_default_force",
        "template_header_mobile_force",
    ):
        if hasattr(View, "_quote_manage_ui_sync_single_template_from_xml"):
            View._quote_manage_ui_sync_single_template_from_xml(key)

    if hasattr(Product, "_quote_manage_ui_backfill_published_product_seo"):
        Product._quote_manage_ui_backfill_published_product_seo()

    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()
