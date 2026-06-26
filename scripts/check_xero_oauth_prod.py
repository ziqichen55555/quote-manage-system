mod = env['ir.module.module'].search([('name', '=', 'account_xero')], limit=1)
print('account_xero:', mod.state if mod else 'missing')
company = env.company
base = env['ir.config_parameter'].sudo().get_param('web.base.url')
redirect = company._xero_redirect_uri()
print('web.base.url:', base)
print('redirect_uri:', redirect)
print('client_id set:', bool(company.xero_client_id))
if company.xero_client_id:
    print('client_id prefix:', company.xero_client_id[:8] + '...')
print('client_secret set:', bool(company.xero_client_secret))
from urllib.parse import urlencode
from odoo.addons.account_xero import const
params = {
    'response_type': 'code',
    'client_id': company.xero_client_id or '',
    'redirect_uri': redirect,
    'scope': const.OAUTH_SCOPES,
    'state': 'test',
}
print('authorize_url_sample:', f"{const.OAUTH_AUTHORIZE_URL}?{urlencode(params)}")
