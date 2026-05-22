# -*- coding: utf-8 -*-
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
