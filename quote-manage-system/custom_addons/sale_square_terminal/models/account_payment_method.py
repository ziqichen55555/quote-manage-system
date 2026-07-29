# -*- coding: utf-8 -*-

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    def _get_payment_method_information(self):
        info = super()._get_payment_method_information()
        info['square'] = {
            'mode': 'multi',
            'domain': [('type', 'in', ('bank', 'cash'))],
        }
        return info

    def _register_hook(self):
        res = super()._register_hook()
        self._ensure_square_method_lines()
        return res

    @api.model
    def _ensure_square_method_lines(self):
        """Ensure Square inbound (+ outbound for refunds) method lines on journals."""
        for payment_type, name in (('inbound', 'Square'), ('outbound', 'Square Refund')):
            method = self.sudo().search([
                ('code', '=', 'square'),
                ('payment_type', '=', payment_type),
            ], limit=1)
            if not method:
                method = self.sudo().create({
                    'name': name if payment_type == 'inbound' else 'Square',
                    'code': 'square',
                    'payment_type': payment_type,
                })

            journals = self.env['account.journal'].sudo().search([
                ('type', 'in', ('bank', 'cash')),
            ])
            if not journals:
                continue

            line_model = self.env['account.payment.method.line'].sudo()
            existing_lines = line_model.search([
                ('payment_method_id', '=', method.id),
                ('journal_id', 'in', journals.ids),
            ])
            existing_journal_ids = set(existing_lines.mapped('journal_id').ids)
            missing_journals = journals.filtered(lambda j: j.id not in existing_journal_ids)
            if not missing_journals:
                continue

            line_model.create([{
                'name': 'Square' if payment_type == 'inbound' else 'Square Refund',
                'payment_method_id': method.id,
                'journal_id': journal.id,
            } for journal in missing_journals])
