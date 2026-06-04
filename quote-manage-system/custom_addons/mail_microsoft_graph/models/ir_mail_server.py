# -*- coding: utf-8 -*-
import base64
import json
import logging
import time

import requests
from email import policy
from email.utils import getaddresses, parseaddr

from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

GRAPH_SEND_URL = 'https://graph.microsoft.com/v1.0/users/{user}/sendMail'
GRAPH_SCOPE = 'https://graph.microsoft.com/Mail.Send'


class _GraphMailSession:
    """Placeholder session so mail.mail.send() skips real SMTP."""

    def __init__(self, mail_server):
        self._mail_server = mail_server

    def quit(self):
        pass

    def close(self):
        pass


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    use_microsoft_graph = fields.Boolean(
        string='Send via Microsoft Graph (HTTPS)',
        help='Use Microsoft Graph sendMail API on port 443 instead of SMTP. '
             'Required when the server blocks outbound SMTP (e.g. DigitalOcean).',
    )

    @api.constrains('use_microsoft_graph', 'smtp_authentication', 'smtp_user')
    def _check_graph_requires_outlook(self):
        for server in self:
            if not server.use_microsoft_graph:
                continue
            if server.smtp_authentication != 'outlook':
                raise UserError(_(
                    'Microsoft Graph delivery requires authentication '
                    '"Outlook OAuth Authentication".'
                ))
            if not server.smtp_user:
                raise UserError(_('Please set the Outlook username (email address).'))

    def _graph_oauth_scope(self):
        return 'offline_access %s' % GRAPH_SCOPE

    def _compute_outlook_uri(self):
        graph_servers = self.filtered('use_microsoft_graph')
        other = self - graph_servers
        if other:
            super(IrMailServer, other)._compute_outlook_uri()
        Config = self.env['ir.config_parameter'].sudo()
        base_url = self.get_base_url()
        client_id = Config.get_param('microsoft_outlook_client_id')
        for record in graph_servers:
            if not record.id or not record.is_microsoft_outlook_configured:
                record.microsoft_outlook_uri = False
                continue
            record.microsoft_outlook_uri = url_join(
                record._get_microsoft_endpoint(),
                'authorize?%s' % url_encode({
                    'client_id': client_id,
                    'response_type': 'code',
                    'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                    'response_mode': 'query',
                    'scope': record._graph_oauth_scope(),
                    'state': json.dumps({
                        'model': record._name,
                        'id': record.id,
                        'csrf_token': record._get_outlook_csrf_token(),
                    }),
                }),
            )

    def _fetch_outlook_token(self, grant_type, **values):
        self.ensure_one()
        if self.use_microsoft_graph:
            Config = self.env['ir.config_parameter'].sudo()
            base_url = self.get_base_url()
            client_id = Config.get_param('microsoft_outlook_client_id')
            client_secret = Config.get_param('microsoft_outlook_client_secret')
            response = requests.post(
                url_join(self._get_microsoft_endpoint(), 'token'),
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': self._graph_oauth_scope(),
                    'redirect_uri': url_join(base_url, '/microsoft_outlook/confirm'),
                    'grant_type': grant_type,
                    **values,
                },
                timeout=15,
            )
            if not response.ok:
                try:
                    error_description = response.json()['error_description']
                except Exception:
                    error_description = _('Unknown error.')
                raise UserError(_(
                    'An error occurred when fetching the access token. %s',
                    error_description,
                ))
            return response.json()
        return super()._fetch_outlook_token(grant_type, **values)

    def _get_graph_access_token(self):
        self.ensure_one()
        now_timestamp = int(time.time())
        if (
            not self.microsoft_outlook_access_token
            or not self.microsoft_outlook_access_token_expiration
            or self.microsoft_outlook_access_token_expiration < now_timestamp
        ):
            if not self.microsoft_outlook_refresh_token:
                raise UserError(_(
                    'Please connect your Outlook account (Connect your Outlook account) '
                    'before sending mail via Microsoft Graph.'
                ))
            (
                self.microsoft_outlook_refresh_token,
                self.microsoft_outlook_access_token,
                self.microsoft_outlook_access_token_expiration,
            ) = self._fetch_outlook_access_token(self.microsoft_outlook_refresh_token)
        return self.microsoft_outlook_access_token

    @api.model
    def connect(self, host=None, port=None, user=None, password=None, encryption=None,
                smtp_from=None, ssl_certificate=None, ssl_private_key=None, smtp_debug=False,
                mail_server_id=None, allow_archived=False):
        if not self._is_test_mode():
            mail_server = None
            if mail_server_id:
                mail_server = self.sudo().browse(mail_server_id)
            elif not host:
                mail_server, _smtp_from = self.sudo()._find_mail_server(smtp_from)
            if mail_server and mail_server.use_microsoft_graph:
                return _GraphMailSession(mail_server)
        return super().connect(
            host=host, port=port, user=user, password=password, encryption=encryption,
            smtp_from=smtp_from, ssl_certificate=ssl_certificate,
            ssl_private_key=ssl_private_key, smtp_debug=smtp_debug,
            mail_server_id=mail_server_id, allow_archived=allow_archived,
        )

    def _graph_recipients(self, addresses):
        recipients = []
        for _name, addr in getaddresses([addresses or '']):
            addr = (addr or '').strip()
            if addr:
                recipients.append({'emailAddress': {'address': addr}})
        return recipients

    def _message_to_graph_body(self, message):
        if message.is_multipart():
            html_part = plain_part = None
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                ctype = part.get_content_type()
                if ctype == 'text/html' and html_part is None:
                    html_part = part.get_content()
                elif ctype == 'text/plain' and plain_part is None:
                    plain_part = part.get_content()
            if html_part:
                return 'HTML', html_part
            if plain_part:
                return 'Text', plain_part
        ctype = message.get_content_type()
        content = message.get_content()
        if ctype == 'text/html':
            return 'HTML', content
        return 'Text', content or ''

    def _message_to_graph_attachments(self, message):
        attachments = []
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get_content_disposition() != 'attachment':
                continue
            name = part.get_filename() or 'attachment'
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            attachments.append({
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': name,
                'contentBytes': base64.b64encode(payload).decode('ascii'),
            })
        return attachments

    def _send_via_graph(self, message):
        self.ensure_one()
        token = self._get_graph_access_token()
        _, smtp_to_list, message = self._prepare_email_message(
            message, _GraphMailSession(self),
        )

        content_type, content = self._message_to_graph_body(message)
        graph_message = {
            'subject': message.get('Subject') or '',
            'body': {
                'contentType': content_type,
                'content': content,
            },
            'toRecipients': self._graph_recipients(message.get('To')),
        }
        cc = self._graph_recipients(message.get('Cc'))
        bcc = self._graph_recipients(message.get('Bcc'))
        if cc:
            graph_message['ccRecipients'] = cc
        if bcc:
            graph_message['bccRecipients'] = bcc

        attachments = self._message_to_graph_attachments(message)
        if attachments:
            graph_message['attachments'] = attachments

        if not graph_message['toRecipients']:
            raise MailDeliveryException(
                _('No valid recipient'),
                _('No valid recipient addresses found.'),
            )

        url = GRAPH_SEND_URL.format(user=requests.utils.quote(self.smtp_user))
        response = requests.post(
            url,
            headers={
                'Authorization': 'Bearer %s' % token,
                'Content-Type': 'application/json',
            },
            json={
                'message': graph_message,
                'saveToSentItems': True,
            },
            timeout=60,
        )
        if not response.ok:
            detail = response.text
            try:
                detail = response.json().get('error', {}).get('message', detail)
            except Exception:
                pass
            raise MailDeliveryException(
                _('Microsoft Graph mail delivery failed'),
                '%s: %s' % (response.status_code, detail),
            )
        _logger.info(
            'Mail sent via Microsoft Graph as %s to %d recipient(s)',
            self.smtp_user, len(smtp_to_list),
        )
        return message.get('Message-Id')

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None):
        server = None
        if isinstance(smtp_session, _GraphMailSession):
            server = smtp_session._mail_server
        elif mail_server_id:
            server = self.sudo().browse(mail_server_id)
        if server and server.use_microsoft_graph:
            if self._is_test_mode():
                return message.get('Message-Id')
            try:
                return server._send_via_graph(message)
            except MailDeliveryException:
                raise
            except Exception as e:
                msg = _('Mail delivery failed via Microsoft Graph.\n%s: %s', e.__class__.__name__, ustr(e))
                _logger.info(msg)
                raise MailDeliveryException(_('Mail Delivery Failed'), msg) from e
        return super().send_email(
            message, mail_server_id=mail_server_id, smtp_server=smtp_server,
            smtp_port=smtp_port, smtp_user=smtp_user, smtp_password=smtp_password,
            smtp_encryption=smtp_encryption, smtp_ssl_certificate=smtp_ssl_certificate,
            smtp_ssl_private_key=smtp_ssl_private_key, smtp_debug=smtp_debug,
            smtp_session=smtp_session,
        )

    def test_smtp_connection(self):
        graph_servers = self.filtered('use_microsoft_graph')
        other = self - graph_servers
        if other:
            return super(IrMailServer, other).test_smtp_connection()
        for server in graph_servers:
            token = server._get_graph_access_token()
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': 'Bearer %s' % token},
                timeout=15,
            )
            if not response.ok:
                detail = response.text
                try:
                    detail = response.json().get('error', {}).get('message', detail)
                except Exception:
                    pass
                raise UserError(_('Microsoft Graph connection test failed:\n%s', detail))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Microsoft Graph connection successful (HTTPS).'),
                'type': 'success',
                'sticky': False,
            },
        }
