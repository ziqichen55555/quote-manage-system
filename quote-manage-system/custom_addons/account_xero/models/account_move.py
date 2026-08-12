# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

from odoo.addons.account_xero import const
from odoo.addons.account_xero.models.xero_notify import xero_client_notification


class AccountMove(models.Model):
    _inherit = 'account.move'

    xero_invoice_id = fields.Char(string='Xero Invoice ID', copy=False, index=True)
    xero_sync_status = fields.Selection(
        const.SYNC_STATUS_SELECTION,
        string='Xero Sync Status',
        copy=False,
        readonly=True,
    )
    xero_sync_message = fields.Text(string='Xero Sync Message', copy=False, readonly=True)

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        invoices = posted.filtered(
            lambda move: move.is_sale_document() and move.move_type == 'out_invoice'
        )
        for move in invoices:
            company = move.company_id
            if not company.xero_enabled or not company.sudo().xero_connected:
                continue
            ok, message = company.sudo()._xero_sync_invoice_safe(move)
            move._xero_post_chatter(_('Xero invoice'), ok, message)
        return posted

    def _xero_post_chatter(self, label, success, message):
        self.ensure_one()
        if not message:
            return
        icon = '✅' if success else '❌'
        self.message_post(
            body=f'<p><strong>{label}</strong> {icon}<br/>{message}</p>',
            subtype_xmlid='mail.mt_note',
        )

    def action_xero_sync(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return xero_client_notification(
                _('Xero'),
                _('Only customer invoices can be synced to Xero.'),
                'warning',
            )
        if self.state != 'posted':
            self.action_post()
        ok, message = self.company_id._xero_sync_invoice_safe(self)
        self._xero_post_chatter(_('Xero invoice (manual)'), ok, message)
        return xero_client_notification(
            _('Xero sync succeeded') if ok else _('Xero sync failed'),
            message,
            'success' if ok else 'danger',
        )

    def action_xero_sync_payments(self):
        """Payments are intentionally not pushed to Xero."""
        self.ensure_one()
        message = _(
            'Payment sync to Xero is disabled. Payment method and status stay in Odoo; '
            'only the invoice is pushed to Xero.'
        )
        return xero_client_notification(_('Xero payment not synced'), message, 'warning')

    def action_xero_sync_all(self):
        self.ensure_one()
        all_ok, message = self._xero_sync_all_single()
        return xero_client_notification(
            _('Xero full sync succeeded') if all_ok else _('Xero full sync failed'),
            message or _('Sync completed.'),
            'success' if all_ok else 'danger',
        )

    def _xero_sync_all_single(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return False, _('Only customer invoices can be synced to Xero.')

        if self.state == 'cancel':
            ok, message = self.company_id._xero_cancel_invoice_safe(self)
            self._xero_post_chatter(_('Xero invoice cancel (manual)'), ok, message)
            return ok, message

        if self.state != 'posted':
            self.action_post()

        ok, message = self.company_id._xero_sync_invoice_safe(self)
        self._xero_post_chatter(_('Xero invoice (manual)'), ok, message)
        return ok, (message or _('Sync completed.'))

    @api.model
    def action_xero_sync_all_company_invoices(self):
        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ('posted', 'cancel')),
            ('company_id', '=', self.env.company.id),
        ])
        if not invoices:
            return xero_client_notification(
                _('Xero sync'),
                _('No posted/cancelled customer invoices found to sync.'),
                'warning',
            )

        success_count = 0
        fail_count = 0
        last_error = ''
        for invoice in invoices:
            ok, message = invoice._xero_sync_all_single()
            if ok:
                success_count += 1
            else:
                fail_count += 1
                if message:
                    last_error = message

        if fail_count:
            msg = _(
                'Bulk sync finished. Success: %(ok)s, Failed: %(fail)s. Last error: %(err)s',
                ok=success_count,
                fail=fail_count,
                err=last_error or '-',
            )
            return xero_client_notification(_('Xero bulk sync finished'), msg, 'warning')

        msg = _(
            'Bulk sync finished. All %(ok)s invoice(s) synced.',
            ok=success_count,
        )
        return xero_client_notification(_('Xero bulk sync finished'), msg, 'success')

    def action_open_xero_sync_logs(self):
        self.ensure_one()
        return {
            'name': _('Xero Sync Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'xero.sync.log',
            'view_mode': 'tree,form',
            'domain': [
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ],
        }
