# -*- coding: utf-8 -*-
"""S00091 payment + stock vs S00092. Read-only."""

SaleOrder = env["sale.order"].sudo()
Payment = env["account.payment"].sudo()
Tx = env["payment.transaction"].sudo()

so = SaleOrder.search([("name", "=", "S00091")], limit=1)
so92 = SaleOrder.search([("name", "=", "S00092")], limit=1)
assert so.exists()

inv = so.invoice_ids[:1]
print("=== S00091 payment truth ===")
print(f"transactions={len(so.transaction_ids)} states={so.transaction_ids.mapped('state')}")
print(
    f"invoice={inv.name if inv else None} payment_state={inv.payment_state if inv else None} "
    f"residual={inv.amount_residual if inv else None}"
)
ar = inv.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable") if inv else None
if ar:
    print(f"AR residual={ar.amount_residual} matched={bool(ar.matched_debit_ids or ar.matched_credit_ids)}")

# Payments reconciled TO this invoice only (via partial reconcile)
reconciled_payments = Payment.browse()
if ar:
    counterpart_moves = (ar.matched_debit_ids.mapped("debit_move_id") | ar.matched_credit_ids.mapped("credit_move_id") |
                         ar.matched_debit_ids.mapped("credit_move_id") | ar.matched_credit_ids.mapped("debit_move_id"))
    counterpart_moves -= ar
    print(f"reconciled counterpart move lines: {len(counterpart_moves)}")
    for ml in counterpart_moves:
        print(f"  {ml.move_id.name} {ml.move_id.move_type} amount={ml.balance}")

# Any Stripe/tx with amount 110 around that date for public partner
txs_110 = Tx.search([
    ("amount", "=", 110.0),
    ("create_date", ">=", "2026-08-10"),
    ("create_date", "<=", "2026-08-12"),
])
print(f"\nAny payment.transaction amount=110 around 11 Aug: {len(txs_110)}")
for tx in txs_110:
    print(f"  {tx.reference} state={tx.state} so={tx.sale_order_ids.mapped('name')} provider={tx.provider_id.name}")

print("\n=== Cancel readiness ===")
print(f"pickings: {[(p.name, p.state) for p in so.picking_ids]}")
print(f"invoice state: {inv.state if inv else None}")
print("SAFE_TO_CANCEL_PAYMENT_SIDE:", len(so.transaction_ids) == 0 and (not inv or inv.payment_state == "not_paid"))

print("\n=== Same product stock vs S00092 ===")
prod = so.order_line.mapped("product_id").filtered(lambda p: p.default_code == "S22A450BW")
print(f"product={prod.default_code} qty_available={prod.qty_available} virtual={prod.virtual_available}")
for order in (so, so92):
    if not order:
        continue
    line = order.order_line.filtered(lambda l: l.product_id == prod)
    moves = line.move_ids
    print(
        f"{order.name}: qty_delivered={line.qty_delivered} "
        f"moves={[(m.state, m.product_uom_qty, m.quantity) for m in moves]} "
        f"picking={[ (p.name, p.state) for p in order.picking_ids ]}"
    )

print("\n=== Who touched S00091 ===")
print(f"create_uid={so.create_uid.name} write_uid={so.write_uid.name} user_id={so.user_id.name or '-'}")
# chatter last notes
messages = so.message_ids[:8]
for m in messages:
    author = m.author_id.name if m.author_id else m.email_from
    body = (m.body or "").replace("\n", " ")[:120]
    print(f"  {m.date} {author}: {body}")
