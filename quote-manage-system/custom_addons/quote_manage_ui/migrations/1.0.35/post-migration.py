# -*- coding: utf-8 -*-
"""1.0.35 post: refine "Follow our journey" newsletter and drop the
"Browse refurbished categories" block from the homepage.

- Resync template archs so the rebuilt s_rw_newsletter (two-column copy +
  Sign up card) and the homepage_custom (no more s_rw_categories t-call)
  overwrite their COW copies in ir.ui.view.
- Bust the frontend asset bundle so the new newsletter SCSS rules land
  immediately.
"""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Page = env['website.page']
    View = env['ir.ui.view']

    if hasattr(Page, '_quote_manage_ui_sync_inline_page_archs_from_module_xml'):
        Page._quote_manage_ui_sync_inline_page_archs_from_module_xml()
    if hasattr(View, '_quote_manage_ui_sync_module_templates_from_xml'):
        View._quote_manage_ui_sync_module_templates_from_xml()
    if hasattr(Page, '_quote_manage_ui_cleanup_duplicate_menus'):
        Page._quote_manage_ui_cleanup_duplicate_menus()

    env['ir.config_parameter'].sudo().set_param(
        'quote_manage_ui.sync_inline_page_arch_from_xml', 'false'
    )

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()

    try:
        env.registry.clear_cache()
    except Exception:
        pass
