"""Diagnose invoice duplicate / payment cascade errors."""
for name in ['INV/2026/00008', 'INV/2026/00009', 'PBNK1/2026/00009']:
    if name.startswith('INV'):
        rec = env['account.move'].sudo().search([('name', '=', name)], limit=1)
    else:
        rec = env['account.payment'].sudo().search([('name', '=', name)], limit=1)
    if not rec:
        print(name, 'NOT FOUND')
        continue
    print('=' * 70, name)
    if rec._name == 'account.move':
        print('  xero_invoice_id:', rec.xero_invoice_id)
        print('  xero_sync_status:', rec.xero_sync_status)
        print('  msg:', rec.xero_sync_message)
        print('  pay state:', rec.payment_state)
    else:
        print('  xero_payment_id:', rec.xero_payment_id)
        print('  xero_sync_status:', rec.xero_sync_status)
        print('  msg:', rec.xero_sync_message)
        print('  reconciled invoices:', rec.reconciled_invoice_ids.mapped('name'))

company = env.company
for inv_name in ['INV/2026/00008']:
    inv = env['account.move'].sudo().search([('name', '=', inv_name)], limit=1)
    if not inv:
        continue
    num = company._xero_invoice_number(inv)
    print('\nXero lookup for invoice number:', num)
    try:
        result = company._xero_request('GET', 'Invoices', params={'where': f'InvoiceNumber=="{num}"'})
        for xinv in result.get('Invoices', []):
            print('  FOUND in Xero:', xinv.get('InvoiceID'), xinv.get('Status'), xinv.get('AmountDue'))
    except Exception as e:
        print('  lookup error:', e)

print('\n--- last invoice errors ---')
for log in env['xero.sync.log'].sudo().search([
    ('operation', '=', 'invoice'), ('status', '=', 'error')
], order='create_date desc', limit=5):
    print(log.create_date, log.res_id, (log.message or '')[:500])
