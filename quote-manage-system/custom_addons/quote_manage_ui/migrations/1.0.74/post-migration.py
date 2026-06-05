# -*- coding: utf-8 -*-
"""1.0.74 — Stop the hero carousel Bootstrap crash for good.

Root cause: the hero carousel shipped with ``data-bs-ride="carousel"``.
Odoo's website editor pauses carousels and strips ``data-bs-slide-to`` from
indicators in edit mode, but Bootstrap's native auto-ride ignores that and
calls ``_setActiveIndicatorElement`` on a null indicator -> TypeError.

Fix: the s_rw_hero snippet no longer sets ``data-bs-ride``; autoplay is driven
on the public site by ``hero_carousel.js`` (which also rebuilds indicators to
match the slides and skips edit mode).

This migration pushes the updated s_rw_hero arch onto the locked module views
(generic + per-website COW copies), normalises any dynamic carousel ids, and
drops the compiled frontend bundles so the new JS/markup is served.
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
