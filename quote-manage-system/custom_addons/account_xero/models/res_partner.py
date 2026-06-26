# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    xero_contact_id = fields.Char(
        string='Xero Contact ID',
        copy=False,
        index=True,
    )
