# -*- coding: utf-8 -*-
"""1.0.37 post: finalize header nav.

- Drop /partners and /shop from the menu (their pages stay reachable by
  direct URL; SHOP is exposed via the header button).
- Reattach the seeded /contactus menu under each website's main menu and
  rename it to "Contact." so it renders in both the desktop nav and the
  mobile offcanvas.
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
