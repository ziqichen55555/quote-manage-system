# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Push every <template> snippet onto its COW copies.
    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_sync_module_templates_from_xml'):
        View._quote_manage_ui_sync_module_templates_from_xml()

    # 2) Push <record model="website.page"> arch (About / Why / Partners)
    #    onto every matching ir.ui.view — these are locked with noupdate=True
    #    so the standard XML loader skips them, hence the explicit force-sync.
    Page = env['website.page']
    if hasattr(Page, '_quote_manage_ui_sync_inline_page_archs_from_module_xml'):
        Page._quote_manage_ui_sync_inline_page_archs_from_module_xml()

    # 3) Drop the cached frontend assets so the new CSS bundle is regenerated.
    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
