# -*- coding: utf-8 -*-
"""1.0.31 post-migration: sync inline page arch onto every COW view, then
reset the one-shot ICP so the next -u doesn't re-sync.

The legacy fix_homepage_view() function in data/website_homepage_fix.xml is
wrapped in noupdate=1, so it does NOT run on -u. We call its sync helper
directly here.
"""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    WebsitePage = env['website.page']

    if hasattr(WebsitePage, '_quote_manage_ui_sync_inline_page_archs_from_module_xml'):
        WebsitePage._quote_manage_ui_sync_inline_page_archs_from_module_xml()

    # One-shot: turn the sync flag off so future -u upgrades don't keep blowing
    # away Website Builder edits.
    env['ir.config_parameter'].sudo().set_param(
        'quote_manage_ui.sync_inline_page_arch_from_xml', 'false'
    )

    # Clear template caches so the new layout (announcement bar, header, footer)
    # is recomputed on next page load.
    try:
        env.registry.clear_cache()
    except Exception:
        pass
