"""Retry Xero sync for invoices 00008-00010."""
names = ['INV/2026/00008', 'INV/2026/00009', 'INV/2026/00010']
for inv_name in names:
    inv = env['account.move'].sudo().search([('name', '=', inv_name)], limit=1)
    if not inv:
        print(inv_name, 'NOT FOUND')
        continue
    company = inv.company_id
    company._xero_sync_invoice_safe(inv)
    inv._xero_sync_reconciled_payments()
    inv.invalidate_recordset()
    print('=' * 50, inv_name)
    print('  invoice sync:', inv.xero_sync_status, inv.xero_invoice_id or '-')
    print('  invoice msg:', (inv.xero_sync_message or '')[:120])
    for pay in inv._get_reconciled_payments():
        print('  payment', pay.name, pay.xero_sync_status, pay.xero_payment_id or '-')
        print('    msg:', (pay.xero_sync_message or '')[:120])
