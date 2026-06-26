"""Inspect Xero sync state for sales orders S00008, S00010 etc."""
orders = env['sale.order'].sudo().search([
    '|', ('name', 'ilike', '0008'), ('name', 'ilike', '0010'),
], order='name')
for so in orders:
    print('=' * 60)
    print('SO:', so.name, '| state:', so.state, '| invoice:', so.invoice_status, '| delivery:', so.delivery_status if 'delivery_status' in so._fields else 'n/a')
    invs = so.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
    for inv in invs:
        print('  INV:', inv.name, '| posted:', inv.state, '| pay:', inv.payment_state)
        print('       xero_invoice_id:', inv.xero_invoice_id or '-')
        print('       xero_sync:', inv.xero_sync_status, '| msg:', (inv.xero_sync_message or '')[:200])
        pays = inv._get_reconciled_payments() if hasattr(inv, '_get_reconciled_payments') else env['account.payment']
        if not pays:
            # fallback
            lines = inv.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
            rec = lines.matched_debit_ids.debit_move_id | lines.matched_credit_ids.credit_move_id
            pays = rec.move_id.payment_id.filtered(lambda p: p.state == 'posted')
        for pay in pays:
            print('    PAY:', pay.name, '| state:', pay.state, '| amount:', pay.amount)
            print('         xero_payment_id:', pay.xero_payment_id or '-')
            print('         xero_sync:', pay.xero_sync_status, '| msg:', (pay.xero_sync_message or '')[:200])
    logs = env['xero.sync.log'].sudo().search([
        ('res_model', 'in', ['account.move', 'account.payment']),
        ('res_id', 'in', (invs.ids + pays.ids if invs else [0])),
    ], order='create_date desc', limit=20)
    for log in logs:
        print('    LOG:', log.create_date, log.operation, log.status, (log.message or '')[:120])

print('\n--- recent xero errors ---')
for log in env['xero.sync.log'].sudo().search([('status', '=', 'error')], order='create_date desc', limit=15):
    rec = env[log.res_model].browse(log.res_id).exists()
    print(log.create_date, log.operation, rec.display_name if rec else log.res_id, (log.message or '')[:180])
