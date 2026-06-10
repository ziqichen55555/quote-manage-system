# -*- coding: utf-8 -*-
"""1.0.80 — Watermarked hero images (cache-bust) + block out-of-stock orders.

1. The two older hero/carousel photos were re-saved with the re-ware logo
   badge, but their filenames were unchanged so browsers / Cloudflare kept
   serving the un-watermarked copies. They've been renamed to ``*-v2.jpg`` so
   the URL changes and every cache is forced to refetch. Module template archs
   are locked (editor-first policy), so ``-u`` alone won't rewrite the stored
   ``s_rw_hero`` arch — force-sync templates from XML and drop the cached
   frontend asset bundles.

2. Storable products must not be over-sold on the shop. Odoo defaults
   ``allow_out_of_stock_order`` to True (keep selling when out of stock), so
   flip it to False on every existing storable product and surface the
   remaining quantity. Services (type != 'product') are left untouched.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Re-sync locked module templates so the renamed hero images take effect.
    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_sync_module_templates_from_xml'):
        View._quote_manage_ui_sync_module_templates_from_xml()

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()

    # 2. Block over-selling on every existing storable product (skip services).
    #    allow_out_of_stock_order / show_availability come from website_sale_stock
    #    (now a declared dependency); guard the write so a missing field can never
    #    abort the upgrade again.
    PT = env['product.template']
    stock_fields = {'allow_out_of_stock_order', 'show_availability'} & set(PT._fields)
    if stock_fields:
        vals = {}
        if 'allow_out_of_stock_order' in stock_fields:
            vals['allow_out_of_stock_order'] = False
        if 'show_availability' in stock_fields:
            vals['show_availability'] = True
        products = PT.sudo().search([('type', '=', 'product')])
        if products:
            products.write(vals)
