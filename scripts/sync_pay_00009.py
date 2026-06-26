pay = env['account.payment'].sudo().search([('name', '=', 'PBNK1/2026/00009')], limit=1)
if pay:
    ok, msg = pay.company_id._xero_sync_payment_safe(pay)
    env.cr.commit()
    print(ok, msg, pay.xero_sync_status)
