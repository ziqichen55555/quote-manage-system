# -*- coding: utf-8 -*-
{
    'name': 'Sale: Square Terminal Payments',
    'version': '17.0.2.0.0',
    'category': 'Sales/Sales',
    'summary': 'Pay Sales Orders via Square Reader app or Square Terminal',
    'description': """
Square card payments for Sales Orders
=====================================
Supports:
* **Reader mode** (default): Odoo creates a pending charge; a store phone/tablet
  app uses Square Mobile Payments SDK + Bluetooth Reader, then reports payment
  back to Odoo.
* **Terminal mode**: classic Terminal API cloud checkout.

On success Odoo invoices, posts payment method Square, and attempts stock delivery.
""",
    'author': 'Co-Creative IT',
    'website': 'https://www.cocreativeit.com',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'sale_stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_payment_method_data.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'wizards/square_terminal_pay_wizard_views.xml',
        'wizards/square_refund_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
