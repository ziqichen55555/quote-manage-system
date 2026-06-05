# -*- coding: utf-8 -*-
"""1.0.72 — Fix homepage hero carousel in Website Editor.

* Stable carousel id (#rwHeroCarousel) instead of a new id on every render.
* Register Carousel snippet options for section.s_rw_hero (nested carousel).
* Patch existing ir.ui.view arch_db that still use rwHeroCarousel{digits}.
* Refresh the s_rw_hero template from XML (snippet library only).

Does NOT run the full template sync (that overwrites Website Builder edits).
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
