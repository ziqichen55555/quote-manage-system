# -*- coding: utf-8 -*-
{
    'name': 'Xero Accounting Bridge',
    'version': '17.0.1.0.1',
    'category': 'Accounting/Accounting',
    'summary': 'Push Re-Ware customer invoices and payments to Co-Creative IT Xero',
    'description': """
Xero Accounting Bridge
======================
One-way sync from Odoo to an existing Xero organisation:

* OAuth 2 connection to Xero
* Customer contacts on first invoice
* Posted customer invoices with Re-Ware tracking category
* Posted customer payments reconciled to synced invoices

Internal Co-Creative IT / Re-Ware module.
""",
    'author': 'Co-Creative IT',
    'website': 'https://www.cocreativeit.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'sale_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/xero_sync_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
