# -*- coding: utf-8 -*-

from odoo import models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    def _get_payment_method_information(self):
        info = super()._get_payment_method_information()
        info['ebay'] = {
            'mode': 'multi',
            'domain': [('type', 'in', ('bank', 'cash'))],
        }
        return info
