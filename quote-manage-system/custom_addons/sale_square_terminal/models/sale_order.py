# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    square_pay_enabled = fields.Boolean(
        related='company_id.square_enabled',
        string='Square Pay Enabled',
    )

    def action_square_pay(self):
        self.ensure_one()
        company = self.company_id
        if not company.square_enabled:
            raise UserError(_(
                'Square Terminal is disabled for this company. '
                'Enable it under Settings → Sales → Square Terminal.'
            ))
        company._square_require_config()

        if self.state not in ('draft', 'sent', 'sale'):
            raise UserError(_('Only quotations and sales orders can be paid with Square.'))
        if self.amount_total <= 0:
            raise UserError(_('Order total must be greater than zero.'))

        posted_invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
        )
        if (
            posted_invoices
            and self.amount_to_invoice <= 0
            and all(m.payment_state in ('paid', 'in_payment') for m in posted_invoices)
        ):
            raise UserError(_('This order is already fully paid.'))

        return {
            'name': _('Pay with Square'),
            'type': 'ir.actions.act_window',
            'res_model': 'square.terminal.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_amount': self.amount_total,
            },
        }

    def _square_fulfill_after_payment(self, checkout, square_payment_id):
        """Confirm SO, invoice, post Square payment, deliver stock."""
        self.ensure_one()
        # 1) Confirm quotation if needed.
        if self.state in ('draft', 'sent'):
            self.action_confirm()

        # 2) Create / reuse customer invoice and post it.
        invoices = self.invoice_ids.filtered(
            lambda m: m.state == 'draft' and m.move_type == 'out_invoice'
        )
        if not invoices and self.invoice_status != 'invoiced':
            invoices = self._create_invoices()
        invoices = (invoices | self.invoice_ids).filtered(
            lambda m: m.move_type == 'out_invoice' and m.state != 'cancel'
        )
        draft = invoices.filtered(lambda m: m.state == 'draft')
        if draft:
            draft.action_post()

        open_invoices = invoices.filtered(
            lambda m: m.state == 'posted'
            and m.payment_state not in ('paid', 'in_payment', 'reversed')
            and m.amount_residual > 0
        )
        if not open_invoices:
            # Maybe already paid in a race; still try to record Square id if payment exists.
            return self.env['account.payment']

        company = self.company_id
        journal = company.square_journal_id or self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not journal:
            raise UserError(_('No bank journal found to record the Square payment.'))

        method_line = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.code == 'square'
        )[:1]
        if not method_line:
            # Ensure lines then retry.
            self.env['account.payment.method']._ensure_square_method_lines()
            method_line = journal.inbound_payment_method_line_ids.filtered(
                lambda l: l.code == 'square'
            )[:1]
        if not method_line:
            raise UserError(_(
                'Square payment method is missing on journal %s. '
                'Upgrade the sale_square_terminal module or add it manually.'
            ) % journal.display_name)

        # Register payment against residual (full open amount for these invoices).
        payments = self.env['account.payment']
        for invoice in open_invoices:
            register = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=invoice.ids,
            ).create({
                'journal_id': journal.id,
                'payment_method_line_id': method_line.id,
                'amount': invoice.amount_residual,
                'communication': self.name,
            })
            payment = register._create_payments()
            payment.write({
                'square_payment_id': square_payment_id or False,
                'square_checkout_id': checkout.get('id') or False,
            })
            payments |= payment

        # 3) Deduct stock: validate outgoing pickings when possible.
        self._square_validate_deliveries()
        return payments

    def _square_validate_deliveries(self):
        """Try to validate related pickings after successful payment.

        Serial/lot tracked lines without assigned lots are left open for staff.
        Payment is already recorded even if delivery cannot complete automatically.
        """
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel')
            and p.picking_type_code == 'outgoing'
        )
        if not pickings:
            return
        pickings.action_assign()
        for picking in pickings:
            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                if move.has_tracking != 'none':
                    continue
                if not move.quantity:
                    move.quantity = move.product_uom_qty
            tracked_unset = picking.move_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
                and m.has_tracking != 'none'
                and not m.move_line_ids.filtered(lambda l: l.lot_id or l.lot_name)
            )
            if tracked_unset:
                continue
            try:
                result = picking.with_context(
                    skip_sms=True,
                    skip_backorder=True,
                    cancel_backorder=True,
                    skip_sanity_check=False,
                ).button_validate()
                # Immediate transfer / backorder wizards: process programmatically if returned.
                if isinstance(result, dict) and result.get('res_model') == 'stock.immediate.transfer':
                    wizard = self.env[result['res_model']].browse(result.get('res_id'))
                    if not wizard and result.get('context'):
                        wizard = self.env[result['res_model']].with_context(
                            **result['context']
                        ).create({})
                    if wizard:
                        wizard.action_confirm()
            except Exception:  # noqa: BLE001 — leave picking open; payment already recorded
                continue
