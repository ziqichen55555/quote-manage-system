# -*- coding: utf-8 -*-
"""1.0.75 — Hero carousel: 7 slides, no Bootstrap ride crash.

* s_rw_hero now has 3 original slides + 4 Grandcarers photos (7 total).
* hero_carousel.js skips Odoo's stock slider on the hero and autoplay
  without Bootstrap ``ride`` (fixes _setActiveIndicatorElement crash).
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_fix_hero_carousel_in_views'):
        View._quote_manage_ui_fix_hero_carousel_in_views()
    if hasattr(View, '_quote_manage_ui_sync_single_template_from_xml'):
        View._quote_manage_ui_sync_single_template_from_xml('s_rw_hero')

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
