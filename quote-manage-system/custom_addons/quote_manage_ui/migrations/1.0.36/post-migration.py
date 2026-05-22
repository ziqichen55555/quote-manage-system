# -*- coding: utf-8 -*-
"""1.0.36 post: header nav rework.

- Drop /shop from the navigation menu (now exposed via the SHOP header
  button instead).
- Rename the seeded /contactus menu to "Contact." and place it right
  after Our Why so it shows up between Our Why and the DONATE button.
- Resync template archs so the new header (DONATE NOW + SHOP buttons,
  no cart icon) and the homepage land on every COW copy.
- Bust the frontend asset bundle so updated SCSS lands immediately.
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
