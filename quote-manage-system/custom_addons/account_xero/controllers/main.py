# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class XeroOAuthController(http.Controller):

    @http.route(
        '/xero/oauth/callback',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def xero_oauth_callback(self, **params):
        error = params.get('error')
        if error:
            message = params.get('error_description') or error
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': message,
            })

        code = params.get('code')
        state = params.get('state')
        if not code or not state:
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': 'Missing authorization code or state.',
            })

        icp = request.env['ir.config_parameter'].sudo()
        state_key = f'account_xero.oauth_state.{state}'
        company_id = icp.get_param(state_key)
        icp.set_param(state_key, False)
        if not company_id:
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': 'OAuth state expired or invalid. Start again from Settings.',
            })

        company = request.env['res.company'].sudo().browse(int(company_id)).exists()
        if not company:
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': 'Company not found for OAuth callback.',
            })

        try:
            company._xero_exchange_code(code)
        except UserError as exc:
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': str(exc.args[0]),
            })
        except Exception as exc:  # noqa: BLE001
            _logger.exception('Xero OAuth callback failed')
            return request.render('account_xero.xero_oauth_result', {
                'success': False,
                'message': str(exc),
            })

        return request.render('account_xero.xero_oauth_result', {
            'success': True,
            'message': company.xero_tenant_name or 'Xero organisation connected.',
        })
