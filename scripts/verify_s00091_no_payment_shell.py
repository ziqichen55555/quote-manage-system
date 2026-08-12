# -*- coding: utf-8 -*-
"""Deep check: does S00091 have any real payment? Read-only."""

SaleOrder = env["sale.order"].sudo()
Payment = env["account.payment"].sudo()
Move = env["account.move"].sudo()
Tx = env["payment.transaction"].sudo()

so = SaleOrder.search([("name", "=", "S00091")], limit=1)
if not so:
    so = SaleOrder.browse(91)
assert so.exists(), "S00091 not found"

print("=" * 72)
print(f"Order {so.name} id={so.id}")
print(f"  state={so.state} invoice_status={so.invoice_status}")
print(f"  amount_untaxed={so.amount_untaxed} amount_tax={so.amount_tax} amount_total={so.amount_total}")
print(f"  partner={so.partner_id.display_name} (id={so.partner_id.id}) is_public={so.partner_id.id == env.ref('base.public_partner').id}")
print(f"  website={so.website_id.name if so.website_id else None}")
print(f"  create_uid={so.create_uid.name} write_uid={so.write_uid.name}")
print(f"  confirmation_date={so.date_order}")

# Payment transactions (Stripe etc.)
txs = so.transaction_ids
print()
print(f"payment.transaction count={len(txs)}")
for tx in txs:
    print(
        f"  tx id={tx.id} ref={tx.reference!r} state={tx.state} "
        f"provider={tx.provider_id.name if tx.provider_id else '-'} "
        f"amount={tx.amount} currency={tx.currency_id.name} "
        f"partner={tx.partner_id.display_name}"
    )
    # provider reference / stripe intent if present
    for fname in ("provider_reference", "stripe_payment_intent", "authorize_txn_id"):
        if fname in tx._fields and tx[fname]:
            print(f"    {fname}={tx[fname]!r}")

# Invoices + payment state + reconciliations
print()
print(f"Invoices count={len(so.invoice_ids)}")
for inv in so.invoice_ids:
    print(
        f"  {inv.name} id={inv.id} state={inv.state} "
        f"payment_state={inv.payment_state} amount_residual={inv.amount_residual} "
        f"amount_total={inv.amount_total}"
    )
    # linked payments via payment move lines / reconciled
    payments = Payment.search([("reconciled_invoice_ids", "in", inv.ids)])
    # also via invoice payment_ids if field exists
    if "payment_ids" in inv._fields:
        payments |= inv.payment_ids
    print(f"    linked account.payment count={len(payments)}")
    for p in payments:
        print(
            f"      payment {p.name} state={p.state} amount={p.amount} "
            f"method={p.payment_method_line_id.name if p.payment_method_line_id else '-'} "
            f"journal={p.journal_id.name}"
        )
    # partial reconcile / outstanding
    for line in inv.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable"):
        print(
            f"    AR line id={line.id} balance={line.balance} "
            f"amount_residual={line.amount_residual} matched={bool(line.matched_debit_ids or line.matched_credit_ids)}"
        )
        for pr in line.matched_debit_ids | line.matched_credit_ids:
            print(f"      reconcile {pr.id} debit_move={pr.debit_move_id.move_id.name} credit_move={pr.credit_move_id.move_id.name}")

# Any payments mentioning this SO in memo/ref
print()
maybe = Payment.search([
    "|", "|",
    ("ref", "ilike", "S00091"),
    ("payment_reference", "ilike", "S00091"),
    ("memo", "ilike", "S00091"),
], limit=20)
print(f"Payments mentioning S00091 in ref/memo: {len(maybe)}")
for p in maybe:
    print(f"  {p.name} state={p.state} amount={p.amount} partner={p.partner_id.display_name}")

# Compare S00092 quickly for same product double-sale risk
so92 = SaleOrder.search([("name", "=", "S00092")], limit=1)
print()
print("=" * 72)
print("Double-sale check vs S00092 (same product?)")
print("=" * 72)
if so92:
    p91 = so.order_line.mapped("product_id")
    p92 = so92.order_line.mapped("product_id")
    overlap = p91 & p92
    print(f"  S00091 products: {[(p.default_code, p.display_name) for p in p91]}")
    print(f"  S00092 products: {[(p.default_code, p.display_name) for p in p92]}")
    print(f"  Overlapping product ids: {overlap.ids}")
    # stock: was qty reduced twice?
    for p in overlap:
        print(
            f"  {p.default_code}: type={p.type} qty_available={p.qty_available} "
            f"virtual={p.virtual_available}"
        )
    # outgoing moves for this product from both orders
    MoveLine = env["stock.move.line"].sudo()
    for order in (so, so92):
        for line in order.order_line.filtered(lambda l: l.product_id in overlap):
            mls = line.move_ids.move_line_ids
            print(
                f"  {order.name} move_lines done_qty={sum(mls.mapped('qty_done'))} "
                f"states={line.move_ids.mapped('state')}"
            )

print()
print("VERDICT HINT:")
print("  If no tx done/authorized AND invoice payment_state=not_paid AND no account.payment → safe to cancel after reversing delivery if needed.")
