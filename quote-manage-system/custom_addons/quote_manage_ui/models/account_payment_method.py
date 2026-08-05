# -*- coding: utf-8 -*-

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    def _get_payment_method_information(self):
        info = super()._get_payment_method_information()
        info['posmachine'] = {
            'mode': 'multi',
            'domain': [('type', 'in', ('bank', 'cash'))],
        }
        return info

    def _register_hook(self):
        res = super()._register_hook()
        self._ensure_posmachine_method_lines()
        return res

    @api.model
    def _ensure_posmachine_method_lines(self):
        """Ensure POS Machine inbound method lines on bank/cash journals."""
        method = self.sudo().search([
            ('code', '=', 'posmachine'),
            ('payment_type', '=', 'inbound'),
        ], limit=1)
        if not method:
            method = self.sudo().create({
                'name': 'POS Machine',
                'code': 'posmachine',
                'payment_type': 'inbound',
            })

        journals = self.env['account.journal'].sudo().search([
            ('type', 'in', ('bank', 'cash')),
        ])
        if not journals:
            return

        line_model = self.env['account.payment.method.line'].sudo()
        existing_lines = line_model.search([
            ('payment_method_id', '=', method.id),
            ('journal_id', 'in', journals.ids),
        ])
        existing_journal_ids = set(existing_lines.mapped('journal_id').ids)
        missing_journals = journals.filtered(lambda j: j.id not in existing_journal_ids)
        if not missing_journals:
            return

        line_model.create([{
            'name': method.name,
            'payment_method_id': method.id,
            'journal_id': journal.id,
        } for journal in missing_journals])
