# -*- coding: utf-8 -*-
"""1.0.79 — Per-category icons on the shop category strip.

The ``reware_products`` shop layout only mapped a ``fa-laptop`` icon for the
"Laptops" category; every other category fell back to a generic ``fa-tag``.
``views/website_templates.xml`` now carries a name -> Font Awesome icon map.

Because module view archs are locked (editor-first policy), ``-u`` alone does
not rewrite the stored arch, so force-sync every module template from XML onto
its DB / COW rows and drop the cached frontend asset bundles.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_sync_module_templates_from_xml'):
        View._quote_manage_ui_sync_module_templates_from_xml()

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
