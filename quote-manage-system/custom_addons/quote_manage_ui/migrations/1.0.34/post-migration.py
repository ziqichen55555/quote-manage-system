# -*- coding: utf-8 -*-
"""1.0.34 post: drop Trade-in / Services, switch to Manrope + coral CTA.

Steps:
- Resync inline page archs and module templates so About / Our Why / etc.
  pick up the rebuilt content from website_templates.xml + snippets.xml.
- Run cleanup_duplicate_menus, which now also unlinks /trade-in and
  /services pages, their COW ir.ui.view rows, the menu items, and the
  ir.model.data references that would otherwise re-seed them on -u.
- Bust the frontend asset bundle so the new Manrope/Nunito Sans @import,
  coral primary buttons and font-weight tweaks take effect immediately.
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
