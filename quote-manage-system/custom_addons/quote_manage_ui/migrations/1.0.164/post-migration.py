# -*- coding: utf-8 -*-
"""1.0.164 — Enforce D-M-Y date format for active English locales."""

from odoo import SUPERUSER_ID, api

_DATE_FORMAT = '%d-%m-%Y'
_TIME_FORMAT = '%I:%M %p'
_TARGET_LANG_CODES = ('en_US', 'en_AU', 'en_GB')


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Lang = env['res.lang'].sudo()
    langs = Lang.search([
        ('active', '=', True),
        ('code', 'in', list(_TARGET_LANG_CODES)),
    ])
    if langs:
        langs.write({
            'date_format': _DATE_FORMAT,
            'time_format': _TIME_FORMAT,
        })
