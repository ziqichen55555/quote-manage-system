# -*- coding: utf-8 -*-
"""1.0.154 — Default date/time + honeypot anti-bot on /book-appointment."""
from xml.etree import ElementTree as ET

from odoo import api, SUPERUSER_ID
from odoo.tools.misc import file_path


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    View = env['ir.ui.view'].sudo()
    Page = env['website.page'].sudo()
    path = file_path('quote_manage_ui/views/website_appointment_templates.xml')
    root = ET.parse(path).getroot()
    page_key, arch_db = Page._quote_manage_ui_read_page_record_xml(
        'book_appointment_page',
        root=root,
    )
    if page_key and arch_db:
        View.search([
            ('key', '=', page_key),
            ('type', '=', 'qweb'),
        ]).write({'arch_db': arch_db})

    env['ir.attachment'].sudo().search([
        ('url', 'like', '/web/assets/%'),
        ('name', 'like', 'web.assets_frontend%'),
    ]).unlink()
