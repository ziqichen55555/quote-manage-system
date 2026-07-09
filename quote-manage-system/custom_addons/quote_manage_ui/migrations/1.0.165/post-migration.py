# -*- coding: utf-8 -*-
"""1.0.165 — Force D-M-Y date format on all active languages."""

from odoo import SUPERUSER_ID, api

_DATE_FORMAT = '%d-%m-%Y'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    langs = env['res.lang'].sudo().search([('active', '=', True)])
    if langs:
        langs.write({'date_format': _DATE_FORMAT})
