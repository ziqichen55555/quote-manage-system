# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_square_refund(self):
        """Open refund wizard for a posted credit note linked to a Square payment."""
        self.ensure_one()
        if self.move_type not in ('out_refund', 'in_refund'):
            raise UserError(_('Square refund is only available on credit notes.'))
        if self.state != 'posted':
            raise UserError(_('Post the credit note before refunding via Square.'))
        if self.payment_state in ('paid', 'in_payment', 'reversed'):
            raise UserError(_('This credit note is already paid or reversed.'))

        return {
            'name': _('Refund via Square'),
            'type': 'ir.actions.act_window',
            'res_model': 'square.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_amount': abs(self.amount_residual),
            },
        }
