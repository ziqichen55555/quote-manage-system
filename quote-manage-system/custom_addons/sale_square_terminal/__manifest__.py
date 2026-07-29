# -*- coding: utf-8 -*-
{
    'name': 'Sale: Square Terminal Payments',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Pay Sales Orders via Square Terminal / Reader (card only)',
    'description': """
Square Terminal payments for Sales Orders
=========================================
Odoo remains the source of truth for products, inventory, pricing and accounting.
Square is used only to take card / EFTPOS payments on a paired Terminal device.

Flow
----
1. Staff open a Sales Order and click **Pay with Square**.
2. Odoo sends a Terminal Checkout to the configured device.
3. Customer taps / inserts / swipes on the Square device.
4. On success Odoo invoices the order, posts an inbound payment with the
   **Square** payment method, and validates deliveries to deduct stock.
5. Refunds: create a credit note, then **Refund via Square** (Square Refunds API).

Credentials (access token, location id, device id) are configured per company
under Settings → Sales → Square Terminal.
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
