# -*- coding: utf-8 -*-
"""Look up INV/2026/00007 and related sale/payment records."""
REF = "INV/2026/00007"

Move = env["account.move"].sudo()
inv = Move.search([("name", "=", REF)], limit=1)
if not inv:
    inv = Move.search([("name", "ilike", "INV/2026/00007")], limit=1)

print("=" * 72)
if not inv:
    print(f"Invoice {REF} not found")
    # try partial
    for m in Move.search([("name", "ilike", "00007"), ("move_type", "in", ("out_invoice", "out_refund"))], limit=10):
        print(f"  candidate: {m.name} state={m.state} partner={m.partner_id.name}")
else:
    print(f"Invoice: {inv.name}")
    print(f"  id={inv.id}  state={inv.state}  payment_state={inv.payment_state}")
    print(f"  type={inv.move_type}  partner={inv.partner_id.name}")
    print(f"  amount={inv.amount_total}  date={inv.invoice_date}")
    print(f"  created={inv.create_date}")
    for line in inv.invoice_line_ids:
        print(f"  line: {line.product_id.default_code or '-'}  {line.name[:50]}  qty={line.quantity}  total={line.price_subtotal}")
    # linked SO
    so_lines = inv.invoice_line_ids.mapped("sale_line_ids.order_id")
    if so_lines:
        for so in so_lines:
            print(f"  sale_order: {so.name}  state={so.state}  delivery={so.delivery_status}")
            for pick in so.picking_ids:
                print(f"    picking: {pick.name}  state={pick.state}")
    payments = inv._get_reconciled_payments()
    print(f"  reconciled payments: {payments.mapped('name')}")

# List payment providers / methods
print()
print("=" * 72)
print("Payment providers (website):")
for p in env["payment.provider"].sudo().search([]):
    print(f"  {p.name}  code={p.code}  state={p.state}  published={p.is_published}")

print()
print("Bank journals / payment methods:")
Journal = env["account.journal"].sudo()
for j in Journal.search([("type", "=", "bank")]):
    print(f"  Journal: {j.name} ({j.code})")
    if hasattr(j, "inbound_payment_method_line_ids"):
        for ml in j.inbound_payment_method_line_ids:
            print(f"    inbound: {ml.name}  code={ml.payment_method_id.code if ml.payment_method_id else '-'}")

print()
print("Done.")
