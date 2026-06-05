# -*- coding: utf-8 -*-
"""1.0.73 — Hero carousel crash guard.

Adds static/src/js/hero_carousel.js which normalises the hero carousel's
active item/indicator state on the public site, preventing Bootstrap's
``_setActiveIndicatorElement`` from throwing
"Cannot read properties of null (reading 'classList')" when a Builder save
left the active classes out of sync.

Also fixes any stored view that still uses a dynamic rwHeroCarousel{digits}
id, and drops the compiled frontend bundles so the new JS is served.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_fix_hero_carousel_in_views'):
        View._quote_manage_ui_fix_hero_carousel_in_views()

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
