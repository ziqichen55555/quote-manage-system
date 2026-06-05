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

Does NOT bulk-sync template archs onto Website Builder COW copies — that
would wipe in-editor homepage/header edits. To redeploy copy from XML once,
set system parameter ``quote_manage_ui.sync_inline_page_arch_from_xml`` to
``true`` before ``-u``. Carousel editor fix ships in 1.0.72.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Rebuild frontend bundles so the new brand-mark SCSS + carousel images
    # are served instead of the cached assets.
    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
