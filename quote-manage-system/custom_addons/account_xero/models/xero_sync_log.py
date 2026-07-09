# -*- coding: utf-8 -*-

from odoo import fields, models


class XeroSyncLog(models.Model):
    _name = 'xero.sync.log'
    _description = 'Xero Sync Log'
    _order = 'create_date desc, id desc'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    operation = fields.Selection(
        [
            ('contact', 'Contact'),
            ('invoice', 'Invoice'),
            ('invoice_cancel', 'Invoice Cancel'),
            ('payment', 'Payment'),
        ],
        required=True,
    )
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    status = fields.Selection(
        [
            ('synced', 'Synced'),
            ('error', 'Error'),
        ],
        required=True,
    )
    message = fields.Text()
    xero_id = fields.Char(string='Xero ID')
    record_name = fields.Char(compute='_compute_record_name')

    def _compute_record_name(self):
        for log in self:
            record = self.env[log.res_model].browse(log.res_id).exists()
            log.record_name = record.display_name if record else False
