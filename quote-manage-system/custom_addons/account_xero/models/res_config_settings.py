# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    xero_enabled = fields.Boolean(related='company_id.xero_enabled', readonly=False)
    xero_client_id = fields.Char(related='company_id.xero_client_id', readonly=False)
    xero_client_secret = fields.Char(related='company_id.xero_client_secret', readonly=False)
    xero_connected = fields.Boolean(related='company_id.xero_connected')
    xero_tenant_name = fields.Char(related='company_id.xero_tenant_name')
    xero_tracking_category_name = fields.Char(
        related='company_id.xero_tracking_category_name',
        readonly=False,
    )
    xero_tracking_option_name = fields.Char(
        related='company_id.xero_tracking_option_name',
        readonly=False,
    )
    xero_invoice_prefix = fields.Char(related='company_id.xero_invoice_prefix', readonly=False)
    xero_revenue_account_code = fields.Char(
        related='company_id.xero_revenue_account_code',
        readonly=False,
    )
    xero_bank_account_code = fields.Char(
        related='company_id.xero_bank_account_code',
        readonly=False,
    )
    xero_default_tax_type = fields.Char(
        related='company_id.xero_default_tax_type',
        readonly=False,
    )
    xero_line_amount_types = fields.Selection(
        related='company_id.xero_line_amount_types',
        readonly=False,
    )

    def action_xero_connect(self):
        return self.company_id.action_xero_connect()

    def action_xero_disconnect(self):
        self.company_id.action_xero_disconnect()
        return True

    def action_xero_test_connection(self):
        return self.company_id.action_xero_test_connection()
