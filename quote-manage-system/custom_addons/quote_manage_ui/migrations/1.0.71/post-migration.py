# -*- coding: utf-8 -*-
"""1.0.71 — Push site copy/branding tweaks from XML onto the live DB.

Stakeholder feedback round:
* "Donate now" CTAs shortened to "Donate" (header, mobile header, hero,
  consultation, Our Why page).
* Re-Ware phone number updated to 0411 882 377 (footer).
* Re-Ware logo mark added next to the "Re-Ware Project" brand in the header.
* Hero carousel now features the Grandcarers WA hand-over photos
  (watermarked with the re-ware logo).
* Shop warranty wording changed from 12-month to 3-month.

Because the module is "editor-first" (layout records are locked noupdate=True
after first load), a plain `-u` won't rewrite the stored arch_db. We reuse the
module's own sync helpers to push both the module <template> archs (header,
footer, snippets/carousel, shop) and the inline website.page archs (Our Why),
then drop the compiled frontend asset bundles so the new SCSS + images load.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    View = env['ir.ui.view']
    if hasattr(View, '_quote_manage_ui_sync_module_templates_from_xml'):
        View._quote_manage_ui_sync_module_templates_from_xml()

    Page = env['website.page']
    if hasattr(Page, '_quote_manage_ui_sync_inline_page_archs_from_module_xml'):
        Page._quote_manage_ui_sync_inline_page_archs_from_module_xml()

    # Rebuild frontend bundles so the new brand-mark SCSS + carousel images
    # are served instead of the cached assets.
    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
