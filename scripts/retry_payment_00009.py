company = env.company.sudo()
company.write({'xero_bank_account_code': '001'})
print('bank code:', company.xero_bank_account_code)
inv = env['account.move'].sudo().search([('name', '=', 'INV/2026/00008')], limit=1)
if inv:
    xid = inv.xero_invoice_id
    print('invoice xero id:', xid)
    if xid:
        detail = company._xero_request('GET', f'Invoices/{xid}')
        xinv = (detail.get('Invoices') or [{}])[0]
        print('xero status:', xinv.get('Status'), 'amount due:', xinv.get('AmountDue'))
        print('xero payments:', xinv.get('Payments'))
    pay = inv._get_reconciled_payments()[:1]
    if pay:
        ok, msg = company._xero_sync_payment_safe(pay)
        print('payment retry:', ok, msg)
