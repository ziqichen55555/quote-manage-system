inv = env['account.move'].sudo().search([('name', '=', 'INV/2026/00008')], limit=1)
if inv:
    ok, msg = inv.company_id._xero_sync_invoice_safe(inv)
    inv._xero_sync_reconciled_payments()
    print('00008 invoice:', ok, msg)
    for pay in inv._get_reconciled_payments():
        print(' payment', pay.name, pay.xero_sync_status, (pay.xero_sync_message or '')[:100])
