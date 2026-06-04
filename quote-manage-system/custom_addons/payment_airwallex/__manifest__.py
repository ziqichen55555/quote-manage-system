# -*- coding: utf-8 -*-
{
    'name': 'Payment Provider: Airwallex',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Accept online payments through Airwallex (Hosted Payment Page)',
    'description': """
Airwallex Payment Provider
==========================
Native Odoo 17 payment.provider integration for Airwallex Hosted Payment Page (HPP).

Why HPP
-------
* Airwallex hosts the card form -> minimum PCI-DSS scope (SAQ-A).
* One integration unlocks cards, Apple Pay, Google Pay, WeChat Pay, Alipay,
  POLi (AU), BECS DD and the rest of Airwallex's payment-method library.
* Multi-currency settles to the merchant's Airwallex global account in AUD,
  USD, HKD, etc. without FX surcharge from a foreign acquirer.

Flow
----
1. Customer hits Odoo /shop/payment, picks "Airwallex".
2. Odoo creates a PaymentIntent on Airwallex via the REST API and stores
   ``intent_id`` + ``client_secret`` on the ``payment.transaction``.
3. Front-end loads ``@airwallex/components-sdk`` and calls
   ``payments.redirectToCheckout()`` -> shopper goes to Airwallex.
4. Airwallex redirects back to ``/payment/airwallex/return`` and POSTs a
   webhook to ``/payment/airwallex/webhook`` (with HMAC signature).
5. The webhook handler verifies the signature and resolves the transaction
   to ``done`` / ``cancel`` / ``error``.

This module is internal to Co-Creative IT / Re-Ware and not published to the
Odoo Apps Store.
""",
    'author': 'Co-Creative IT',
    'website': 'https://www.cocreativeit.com',
    'license': 'LGPL-3',
    'depends': [
        'payment',
    ],
    'data': [
        'views/payment_airwallex_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_airwallex/static/src/js/payment_form.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
