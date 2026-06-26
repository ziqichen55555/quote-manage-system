company = env.company.sudo()
company.write({'xero_bank_account_code': '001'})
inv = env['account.move'].sudo().search([('name', '=', 'INV/2026/00008')], limit=1)
ok, msg = company._xero_sync_invoice_safe(inv)
env.cr.commit()
inv.invalidate_recordset()
print('invoice:', ok, inv.xero_invoice_id, msg)
if inv.xero_invoice_id:
    detail = company._xero_request('GET', f'Invoices/{inv.xero_invoice_id}')
    xinv = (detail.get('Invoices') or [{}])[0]
    print('xero status:', xinv.get('Status'), 'due:', xinv.get('AmountDue'), 'paid:', xinv.get('AmountPaid'))
    print('payments on invoice:', len(xinv.get('Payments') or []))
