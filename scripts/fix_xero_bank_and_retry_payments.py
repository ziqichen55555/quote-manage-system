env.company.sudo().write({'xero_bank_account_code': '001'})
print('Updated bank account code to 001')
for inv_name in ['INV/2026/00008', 'INV/2026/00010']:
    inv = env['account.move'].sudo().search([('name', '=', inv_name)], limit=1)
    if not inv:
        continue
    inv._xero_sync_reconciled_payments()
    for pay in inv._get_reconciled_payments():
        print(inv_name, pay.name, pay.xero_sync_status, pay.xero_payment_id or '-', (pay.xero_sync_message or '')[:80])
