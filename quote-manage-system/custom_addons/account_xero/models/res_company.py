# -*- coding: utf-8 -*-

import json
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urljoin

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.account_xero import const
from odoo.addons.account_xero.models.xero_notify import xero_short_api_error

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    xero_enabled = fields.Boolean(
        string='Sync to Xero',
        help='Push posted customer invoices and payments to Xero.',
    )
    xero_client_id = fields.Char(string='Xero Client ID', groups='base.group_system')
    xero_client_secret = fields.Char(string='Xero Client Secret', groups='base.group_system')
    xero_access_token = fields.Char(groups='base.group_system')
    xero_refresh_token = fields.Char(groups='base.group_system')
    xero_token_expires_at = fields.Datetime(groups='base.group_system')
    xero_tenant_id = fields.Char(string='Xero Tenant ID', groups='base.group_system')
    xero_tenant_name = fields.Char(string='Xero Organisation', readonly=True)
    xero_connected = fields.Boolean(compute='_compute_xero_connected')

    xero_tracking_category_name = fields.Char(
        string='Tracking Category',
        default=const.DEFAULT_TRACKING_CATEGORY_NAME,
    )
    xero_tracking_option_name = fields.Char(
        string='Tracking Option',
        default=const.DEFAULT_TRACKING_OPTION_NAME,
        help='Applied to every invoice line so Re-Ware sales can be filtered in Xero.',
    )
    xero_invoice_prefix = fields.Char(
        string='Invoice Number Prefix',
        default=const.DEFAULT_INVOICE_PREFIX,
        help='Prepended to Odoo invoice numbers in Xero when missing.',
    )
    xero_revenue_account_code = fields.Char(
        string='Revenue Account Code',
        default=const.DEFAULT_REVENUE_ACCOUNT_CODE,
        help='Xero account code used on sales invoice lines.',
    )
    xero_bank_account_code = fields.Char(
        string='Bank Account Code',
        default=const.DEFAULT_BANK_ACCOUNT_CODE,
        help='Xero bank account used when recording customer payments.',
    )
    xero_default_tax_type = fields.Char(
        string='Sales Tax Type',
        default=const.DEFAULT_TAX_TYPE,
        help='Xero tax type for GST on sales (commonly OUTPUT in AU orgs).',
    )
    xero_line_amount_types = fields.Selection(
        [
            ('Exclusive', 'Tax exclusive'),
            ('Inclusive', 'Tax inclusive'),
            ('NoTax', 'No tax'),
        ],
        string='Line Amount Type',
        default=const.DEFAULT_LINE_AMOUNT_TYPES,
        required=True,
    )

    @api.depends('xero_access_token', 'xero_tenant_id')
    def _compute_xero_connected(self):
        for company in self:
            company.xero_connected = bool(
                company.xero_access_token and company.xero_tenant_id
            )

    def _xero_redirect_uri(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return urljoin(base_url.rstrip('/') + '/', 'xero/oauth/callback')

    def _xero_check_configured(self):
        self.ensure_one()
        if not self.xero_client_id or not self.xero_client_secret:
            raise UserError(_(
                'Enter the Xero Client ID and Client Secret under '
                'Settings → Accounting → Xero Integration.'
            ))

    def action_xero_connect(self):
        self.ensure_one()
        self._xero_check_configured()
        nonce = secrets.token_urlsafe(24)
        self.env['ir.config_parameter'].sudo().set_param(
            f'account_xero.oauth_state.{nonce}',
            str(self.id),
        )
        params = {
            'response_type': 'code',
            'client_id': self.xero_client_id,
            'redirect_uri': self._xero_redirect_uri(),
            'scope': const.OAUTH_SCOPES,
            'state': nonce,
        }
        return {
            'type': 'ir.actions.act_url',
            'url': f'{const.OAUTH_AUTHORIZE_URL}?{urlencode(params)}',
            'target': 'self',
        }

    def action_xero_disconnect(self):
        for company in self:
            company.write({
                'xero_access_token': False,
                'xero_refresh_token': False,
                'xero_token_expires_at': False,
                'xero_tenant_id': False,
                'xero_tenant_name': False,
            })

    def action_xero_test_connection(self):
        self.ensure_one()
        org_name = self._xero_request('GET', 'Organisation')['Organisations'][0]['Name']
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Xero connection OK'),
                'message': _('Connected to %s', org_name),
                'type': 'success',
                'sticky': False,
            },
        }

    def _xero_exchange_code(self, code):
        self.ensure_one()
        response = requests.post(
            const.OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self._xero_redirect_uri(),
            },
            auth=(self.xero_client_id, self.xero_client_secret),
            timeout=30,
        )
        if response.status_code >= 400:
            raise UserError(_(
                'Xero authorization failed (%(status)s): %(body)s',
                status=response.status_code,
                body=response.text[:500],
            ))
        payload = response.json()
        self._xero_store_tokens(payload)
        self._xero_bind_tenant()

    def _xero_store_tokens(self, payload):
        self.ensure_one()
        expires_in = int(payload.get('expires_in', 1800))
        self.write({
            'xero_access_token': payload.get('access_token'),
            'xero_refresh_token': payload.get('refresh_token', self.xero_refresh_token),
            'xero_token_expires_at': fields.Datetime.now() + timedelta(seconds=max(expires_in - 60, 60)),
        })

    def _xero_bind_tenant(self):
        self.ensure_one()
        response = requests.get(
            const.OAUTH_CONNECTIONS_URL,
            headers={'Authorization': f'Bearer {self.xero_access_token}'},
            timeout=30,
        )
        if response.status_code >= 400:
            raise UserError(_(
                'Could not list Xero organisations (%(status)s): %(body)s',
                status=response.status_code,
                body=response.text[:500],
            ))
        connections = response.json()
        if not connections:
            raise UserError(_('No Xero organisation is authorised for this app.'))
        tenant = connections[0]
        self.write({
            'xero_tenant_id': tenant.get('tenantId'),
            'xero_tenant_name': tenant.get('tenantName'),
            'xero_enabled': True,
        })

    def _xero_refresh_access_token(self):
        self.ensure_one()
        if not self.xero_refresh_token:
            raise UserError(_('Xero session expired. Please reconnect under Settings.'))
        response = requests.post(
            const.OAUTH_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.xero_refresh_token,
            },
            auth=(self.xero_client_id, self.xero_client_secret),
            timeout=30,
        )
        if response.status_code >= 400:
            _logger.error('Xero token refresh failed: %s', response.text)
            raise UserError(_(
                'Xero session expired and could not be refreshed. '
                'Please reconnect under Settings.'
            ))
        self._xero_store_tokens(response.json())

    def _xero_ensure_token(self):
        self.ensure_one()
        if not self.xero_access_token:
            raise UserError(_('Xero is not connected. Open Settings and click Connect to Xero.'))
        if self.xero_token_expires_at and self.xero_token_expires_at <= fields.Datetime.now():
            self._xero_refresh_access_token()

    def _xero_request(self, method, endpoint, payload=None, params=None):
        self.ensure_one()
        self._xero_ensure_token()
        url = f'{const.API_BASE_URL}/{endpoint.lstrip("/")}'
        headers = {
            'Authorization': f'Bearer {self.xero_access_token}',
            'xero-tenant-id': self.xero_tenant_id,
            'Accept': 'application/json',
        }
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            params=params,
            timeout=60,
        )
        if response.status_code == 401:
            self._xero_refresh_access_token()
            headers['Authorization'] = f'Bearer {self.xero_access_token}'
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                params=params,
                timeout=60,
            )
        if response.status_code >= 400:
            body = response.text[:1000]
            raise UserError(_(
                'Xero API error on %(endpoint)s (%(status)s): %(body)s',
                endpoint=endpoint,
                status=response.status_code,
                body=body,
            ))
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def _xero_log(self, operation, res_model, res_id, status, message='', xero_id=False):
        self.ensure_one()
        return self.env['xero.sync.log'].sudo().create({
            'company_id': self.id,
            'operation': operation,
            'res_model': res_model,
            'res_id': res_id,
            'status': status,
            'message': message,
            'xero_id': xero_id or False,
        })

    def _xero_invoice_number(self, move):
        self.ensure_one()
        prefix = (self.xero_invoice_prefix or '').strip()
        name = (move.name or move.ref or str(move.id)).strip()
        if prefix and not name.upper().startswith(prefix.upper()):
            return f'{prefix}{name}'
        return name

    def _xero_map_tax_type(self, tax):
        self.ensure_one()
        if not tax:
            return 'NONE' if self.xero_line_amount_types == 'NoTax' else self.xero_default_tax_type
        if not tax.amount:
            return 'NONE'
        return self.xero_default_tax_type

    def _xero_tracking_payload(self):
        self.ensure_one()
        category = (self.xero_tracking_category_name or '').strip()
        option = (self.xero_tracking_option_name or '').strip()
        if not category or not option:
            return []
        return [{'Name': category, 'Option': option}]

    def _xero_find_contact_id(self, partner):
        """Return an existing Xero contact ID if the partner already exists there."""
        self.ensure_one()
        partner = partner.commercial_partner_id
        name = (partner.name or '').replace('"', '\\"').strip()
        if name:
            result = self._xero_request('GET', 'Contacts', params={'where': f'Name=="{name}"'})
            contacts = result.get('Contacts') or []
            if contacts:
                return contacts[0]['ContactID']
        email = (partner.email or '').strip()
        if email:
            safe_email = email.replace('"', '\\"')
            result = self._xero_request('GET', 'Contacts', params={
                'where': f'EmailAddress=="{safe_email}"',
            })
            contacts = result.get('Contacts') or []
            if contacts:
                return contacts[0]['ContactID']
        return False

    def _xero_sync_contact(self, partner):
        self.ensure_one()
        partner = partner.commercial_partner_id
        if partner.xero_contact_id:
            return partner.xero_contact_id

        existing_id = self._xero_find_contact_id(partner)
        if existing_id:
            partner.sudo().write({'xero_contact_id': existing_id})
            self._xero_log(
                'contact', 'res.partner', partner.id, 'synced',
                _('Linked existing Xero contact for %s', partner.display_name),
                existing_id,
            )
            return existing_id

        contact_vals = {
            'Name': partner.name or _('Customer'),
            'ContactStatus': 'ACTIVE',
        }
        email = (partner.email or '').strip()
        if email:
            contact_vals['EmailAddress'] = email
        if partner.phone:
            contact_vals['Phones'] = [{
                'PhoneType': 'DEFAULT',
                'PhoneNumber': partner.phone,
            }]
        if partner.street or partner.city or partner.zip:
            contact_vals['Addresses'] = [{
                'AddressType': 'STREET',
                'AddressLine1': partner.street or '',
                'City': partner.city or '',
                'Region': partner.state_id.name if partner.state_id else '',
                'PostalCode': partner.zip or '',
                'Country': partner.country_id.code if partner.country_id else '',
            }]

        result = self._xero_request('POST', 'Contacts', {'Contacts': [contact_vals]})
        contacts = result.get('Contacts') or []
        if not contacts:
            raise UserError(_('Xero did not return a contact ID for %s', partner.display_name))
        contact_id = contacts[0]['ContactID']
        partner.sudo().write({'xero_contact_id': contact_id})
        self._xero_log('contact', 'res.partner', partner.id, 'synced', partner.display_name, contact_id)
        return contact_id

    def _xero_build_line_description(self, line):
        parts = [(line.name or line.product_id.display_name or '').strip()]
        if line.move_id.move_type == 'out_invoice':
            lot_values = line.move_id._get_invoiced_lot_values()
            product_lots = [
                lot['lot_name']
                for lot in lot_values
                if lot.get('product_name') == line.product_id.display_name
            ]
            if not product_lots and line.sale_line_ids:
                lots = line.sale_line_ids.move_ids.move_line_ids.filtered(
                    lambda ml: ml.state == 'done' and ml.lot_id and ml.product_id == line.product_id
                ).mapped('lot_id.name')
                product_lots = sorted(set(lots))
            for lot_name in product_lots:
                parts.append(f'S/N: {lot_name}')
        description = '\n'.join(part for part in parts if part)
        return description[:4000] or line.product_id.display_name or 'Item'

    def _xero_build_invoice_payload(self, move, contact_id):
        self.ensure_one()
        line_items = []
        for line in move.invoice_line_ids.filtered(
            lambda aml: aml.display_type == 'product' and aml.product_id
        ):
            tax_type = self._xero_map_tax_type(line.tax_ids[:1])
            item = {
                'Description': self._xero_build_line_description(line),
                'Quantity': line.quantity,
                'UnitAmount': line.price_unit,
                'AccountCode': self.xero_revenue_account_code,
                'TaxType': tax_type,
            }
            tracking = self._xero_tracking_payload()
            if tracking:
                item['Tracking'] = tracking
            line_items.append(item)

        if not line_items:
            raise UserError(_('Invoice %s has no product lines to send to Xero.', move.display_name))

        invoice_date = fields.Date.to_string(move.invoice_date or move.date)
        due_date = fields.Date.to_string(move.invoice_date_due or move.invoice_date or move.date)
        reference = move.invoice_origin or move.ref or move.payment_reference or ''

        return {
            'Invoices': [{
                'Type': 'ACCREC',
                'Contact': {'ContactID': contact_id},
                'Date': invoice_date,
                'DueDate': due_date,
                'InvoiceNumber': self._xero_invoice_number(move),
                'Reference': reference,
                'LineAmountTypes': self.xero_line_amount_types,
                'LineItems': line_items,
                'Status': 'AUTHORISED',
            }],
        }

    def _xero_find_invoice_id(self, move):
        """Find an existing Xero sales invoice by our invoice number."""
        self.ensure_one()
        number = self._xero_invoice_number(move).replace('"', '\\"').strip()
        if not number:
            return False
        result = self._xero_request('GET', 'Invoices', params={
            'where': f'InvoiceNumber=="{number}"',
        })
        invoices = result.get('Invoices') or []
        if invoices:
            return invoices[0]['InvoiceID']
        return False

    def _xero_sync_invoice(self, move):
        self.ensure_one()
        if move.xero_invoice_id:
            message = _(
                'Invoice already exists in Xero (ID: %(xero_id)s).',
                xero_id=move.xero_invoice_id,
            )
            move.sudo().write({
                'xero_sync_status': 'synced',
                'xero_sync_message': message,
            })
            return move.xero_invoice_id
        if move.move_type != 'out_invoice' or move.state != 'posted':
            message = _('Only posted customer invoices can be synced to Xero.')
            move.sudo().write({
                'xero_sync_status': 'skipped',
                'xero_sync_message': message,
            })
            return False

        contact_id = self._xero_sync_contact(move.partner_id)
        existing_id = self._xero_find_invoice_id(move)
        if existing_id:
            invoice_number = self._xero_invoice_number(move)
            message = _(
                'Linked to existing Xero invoice %(number)s (ID: %(xero_id)s). '
                'It was already in Xero from a previous sync.',
                number=invoice_number,
                xero_id=existing_id,
            )
            move.sudo().write({
                'xero_invoice_id': existing_id,
                'xero_sync_status': 'synced',
                'xero_sync_message': message,
            })
            self._xero_log('invoice', 'account.move', move.id, 'synced', message, existing_id)
            return existing_id

        payload = self._xero_build_invoice_payload(move, contact_id)
        result = self._xero_request('POST', 'Invoices', payload)
        invoices = result.get('Invoices') or []
        if not invoices:
            raise UserError(_('Xero did not return an invoice ID for %s', move.display_name))

        xero_invoice_id = invoices[0]['InvoiceID']
        invoice_number = self._xero_invoice_number(move)
        message = _(
            'Invoice synced to Xero as %(number)s (ID: %(xero_id)s).',
            number=invoice_number,
            xero_id=xero_invoice_id,
        )
        move.sudo().write({
            'xero_invoice_id': xero_invoice_id,
            'xero_sync_status': 'synced',
            'xero_sync_message': message,
        })
        self._xero_log('invoice', 'account.move', move.id, 'synced', message, xero_invoice_id)
        return xero_invoice_id

    def _xero_sync_payment(self, payment):
        self.ensure_one()
        if payment.xero_payment_id:
            message = _(
                'Payment already exists in Xero (ID: %(xero_id)s).',
                xero_id=payment.xero_payment_id,
            )
            payment.sudo().write({
                'xero_sync_status': 'synced',
                'xero_sync_message': message,
            })
            return payment.xero_payment_id
        if payment.payment_type != 'inbound' or payment.partner_type != 'customer':
            message = _('Only inbound customer payments are synced to Xero.')
            payment.sudo().write({
                'xero_sync_status': 'skipped',
                'xero_sync_message': message,
            })
            return False
        if payment.state != 'posted':
            message = _('Payment must be posted in Odoo before syncing to Xero.')
            payment.sudo().write({
                'xero_sync_status': 'skipped',
                'xero_sync_message': message,
            })
            return False

        invoices = payment.reconciled_invoice_ids.filtered(
            lambda inv: inv.move_type == 'out_invoice' and inv.company_id == self
        )
        if not invoices:
            message = _(
                'No reconciled customer invoice found. Register the payment on the '
                'invoice in Odoo first, then sync again.'
            )
            payment.sudo().write({
                'xero_sync_status': 'skipped',
                'xero_sync_message': message,
            })
            return False

        for invoice in invoices:
            if not invoice.xero_invoice_id:
                self._xero_sync_invoice_safe(invoice)

        invoice = invoices.filtered('xero_invoice_id')[:1]
        if not invoice:
            names = ', '.join(invoices.mapped('display_name'))
            raise UserError(_(
                'Payment %(payment)s is linked to invoice(s) %(invoices)s that are '
                'not in Xero yet. Open each invoice and click Push to Xero first.',
                payment=payment.display_name,
                invoices=names,
            ))

        detail = self._xero_request('GET', f'Invoices/{invoice.xero_invoice_id}')
        xero_invoice = (detail.get('Invoices') or [{}])[0]
        if xero_invoice.get('Status') == 'PAID' or not float(xero_invoice.get('AmountDue') or 0):
            existing_payments = xero_invoice.get('Payments') or []
            xero_payment_id = existing_payments[0].get('PaymentID') if existing_payments else False
            message = _(
                'Invoice %(invoice)s is already Paid in Xero (no duplicate payment created).',
                invoice=invoice.display_name,
            )
            payment.sudo().write({
                'xero_payment_id': xero_payment_id or False,
                'xero_sync_status': 'synced',
                'xero_sync_message': message,
            })
            self._xero_log('payment', 'account.payment', payment.id, 'synced', message, xero_payment_id)
            return xero_payment_id or True

        payment_date = fields.Date.to_string(payment.date)
        payload = {
            'Payments': [{
                'Invoice': {'InvoiceID': invoice.xero_invoice_id},
                'Account': {'Code': self.xero_bank_account_code},
                'Date': payment_date,
                'Amount': payment.amount,
                'Reference': payment.payment_reference or payment.name or invoice.name,
            }],
        }
        result = self._xero_request('POST', 'Payments', payload)
        payments = result.get('Payments') or []
        if not payments:
            raise UserError(_('Xero did not return a payment ID for %s', payment.display_name))

        xero_payment_id = payments[0]['PaymentID']
        message = _(
            'Payment of %(amount)s synced to Xero for invoice %(invoice)s (ID: %(xero_id)s).',
            amount=payment.amount,
            invoice=invoice.display_name,
            xero_id=xero_payment_id,
        )
        payment.sudo().write({
            'xero_payment_id': xero_payment_id,
            'xero_sync_status': 'synced',
            'xero_sync_message': message,
        })
        self._xero_log(
            'payment', 'account.payment', payment.id, 'synced',
            message, xero_payment_id,
        )
        return xero_payment_id

    def _xero_sync_invoice_safe(self, move):
        """Sync invoice to Xero. Returns (success, user_message)."""
        self.ensure_one()
        if not self.xero_enabled:
            message = _('Xero sync is turned off. Enable it under Accounting → Xero Integration.')
            move.sudo().write({'xero_sync_status': 'skipped', 'xero_sync_message': message})
            return False, message
        if not self.xero_connected:
            message = _('Xero is not connected. Open Settings and click Connect to Xero.')
            move.sudo().write({'xero_sync_status': 'error', 'xero_sync_message': message})
            return False, message
        try:
            with self.env.cr.savepoint():
                xero_id = self._xero_sync_invoice(move)
                move.invalidate_recordset(['xero_sync_status', 'xero_sync_message'])
                if xero_id:
                    return True, move.xero_sync_message or _('Invoice synced to Xero.')
                return False, move.xero_sync_message or _('Invoice was not synced to Xero.')
        except UserError as exc:
            message = xero_short_api_error(str(exc.args[0]))
            move.sudo().write({
                'xero_sync_status': 'error',
                'xero_sync_message': message,
            })
            self._xero_log('invoice', 'account.move', move.id, 'error', message)
            _logger.warning('Xero invoice sync failed for %s: %s', move.display_name, exc)
            return False, message
        except Exception as exc:  # noqa: BLE001
            message = xero_short_api_error(str(exc))
            move.sudo().write({
                'xero_sync_status': 'error',
                'xero_sync_message': message,
            })
            self._xero_log('invoice', 'account.move', move.id, 'error', message)
            _logger.exception('Xero invoice sync failed for %s', move.display_name)
            return False, message

    def _xero_sync_payment_safe(self, payment):
        """Sync payment to Xero. Returns (success, user_message)."""
        self.ensure_one()
        if not self.xero_enabled:
            message = _('Xero sync is turned off. Enable it under Accounting → Xero Integration.')
            payment.sudo().write({'xero_sync_status': 'skipped', 'xero_sync_message': message})
            return False, message
        if not self.xero_connected:
            message = _('Xero is not connected. Open Settings and click Connect to Xero.')
            payment.sudo().write({'xero_sync_status': 'error', 'xero_sync_message': message})
            return False, message
        try:
            with self.env.cr.savepoint():
                xero_id = self._xero_sync_payment(payment)
                payment.invalidate_recordset(['xero_sync_status', 'xero_sync_message'])
                if xero_id:
                    return True, payment.xero_sync_message or _('Payment synced to Xero.')
                return False, payment.xero_sync_message or _('Payment was not synced to Xero.')
        except UserError as exc:
            message = xero_short_api_error(str(exc.args[0]))
            payment.sudo().write({
                'xero_sync_status': 'error',
                'xero_sync_message': message,
            })
            self._xero_log('payment', 'account.payment', payment.id, 'error', message)
            _logger.warning('Xero payment sync failed for %s: %s', payment.display_name, exc)
            return False, message
        except Exception as exc:  # noqa: BLE001
            message = xero_short_api_error(str(exc))
            payment.sudo().write({
                'xero_sync_status': 'error',
                'xero_sync_message': message,
            })
            self._xero_log('payment', 'account.payment', payment.id, 'error', message)
            _logger.exception('Xero payment sync failed for %s', payment.display_name)
            return False, message
