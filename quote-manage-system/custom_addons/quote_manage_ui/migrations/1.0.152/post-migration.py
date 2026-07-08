# -*- coding: utf-8 -*-
"""1.0.152 — Hero: show Shop CTA beside Learn more / Donate on mobile."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    View = env['ir.ui.view'].sudo()
    if hasattr(View, '_quote_manage_ui_sync_single_template_from_xml'):
        View._quote_manage_ui_sync_single_template_from_xml('s_rw_hero')
    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
