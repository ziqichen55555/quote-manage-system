# -*- coding: utf-8 -*-
"""Xero OAuth and Accounting API constants."""

OAUTH_AUTHORIZE_URL = 'https://login.xero.com/identity/connect/authorize'
OAUTH_TOKEN_URL = 'https://identity.xero.com/connect/token'
OAUTH_CONNECTIONS_URL = 'https://api.xero.com/connections'
API_BASE_URL = 'https://api.xero.com/api.xro/2.0'

OAUTH_SCOPES = ' '.join([
    'openid',
    'profile',
    'email',
    'offline_access',
    'accounting.contacts',
    # Broad accounting.transactions is rejected for apps created after Mar 2026.
    'accounting.invoices',
    'accounting.payments',
    'accounting.settings.read',
])

DEFAULT_TRACKING_CATEGORY_NAME = 'Sales Channel'
DEFAULT_TRACKING_OPTION_NAME = 'Re-Ware'
DEFAULT_INVOICE_PREFIX = 'RW-'
DEFAULT_REVENUE_ACCOUNT_CODE = '200'
DEFAULT_BANK_ACCOUNT_CODE = '001'
DEFAULT_TAX_TYPE = 'OUTPUT'
DEFAULT_LINE_AMOUNT_TYPES = 'Exclusive'

SYNC_STATUS_SELECTION = [
    ('pending', 'Pending'),
    ('synced', 'Synced'),
    ('error', 'Error'),
    ('skipped', 'Skipped'),
]
