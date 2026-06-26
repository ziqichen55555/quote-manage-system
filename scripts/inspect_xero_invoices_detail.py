"""Full detail for INV 00008 00009 00010 and contact errors."""
for inv_name in ['INV/2026/00008', 'INV/2026/00009', 'INV/2026/00010']:
    inv = env['account.move'].sudo().search([('name', '=', inv_name)], limit=1)
    if not inv:
        print(inv_name, 'NOT FOUND')
        continue
    p = inv.partner_id.commercial_partner_id
    print('=' * 70)
    print(inv_name, 'SO:', inv.invoice_origin, 'pay:', inv.payment_state)
    print('  partner:', repr(p.name), '| email:', repr(p.email), '| phone:', repr(p.phone))
    print('  street:', repr(p.street), 'city:', repr(p.city), 'zip:', repr(p.zip))
    print('  xero_invoice_id:', inv.xero_invoice_id, 'sync:', inv.xero_sync_status)
    print('  msg:', (inv.xero_sync_message or '')[:300])
    pays = inv._get_reconciled_payments()
    for pay in pays:
        ref = getattr(pay, 'memo', None) or getattr(pay, 'payment_reference', None) or getattr(pay, 'ref', None)
        print('  payment:', pay.name, pay.amount, 'xero_pay:', pay.xero_payment_id, 'sync:', pay.xero_sync_status)
        print('    ref fields:', ref, '| msg:', (pay.xero_sync_message or '')[:200])
