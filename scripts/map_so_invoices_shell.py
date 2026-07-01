# -*- coding: utf-8 -*-
"""Map every sale order to invoices — find mismatches."""
SO = env["sale.order"].sudo()
Move = env["account.move"].sudo()

sos = SO.search([("state", "!=", "cancel")], order="name desc")
draft_invs = Move.search(
    [("move_type", "=", "out_invoice"), ("state", "=", "draft")],
    order="create_date desc",
)

print("=" * 90)
print("SALE ORDER  <->  INVOICE MAP")
print("=" * 90)
print(f"{'SO':<8} {'Customer':<22} {'SO Total':>10}  {'Invoices':<40} {'Inv Total':>10}  Match?")
print("-" * 90)

mismatch = []
for so in sos:
    invs = so.invoice_ids.filtered(lambda m: m.move_type in ("out_invoice", "out_refund"))
    inv_names = ", ".join(invs.mapped("name")) or "(none)"
    inv_total = sum(invs.filtered(lambda m: m.state == "posted" and m.move_type == "out_invoice").mapped("amount_total"))
    inv_total -= sum(invs.filtered(lambda m: m.state == "posted" and m.move_type == "out_refund").mapped("amount_total"))
    so_total = so.amount_total
    ok = abs(so_total - inv_total) < 0.02 if invs else False
    flag = "OK" if ok else "MISMATCH"
    if not ok:
        mismatch.append(so)
    # product summary
    prods = " + ".join((l.product_id.default_code or "?")[:20] for l in so.order_line[:2])
    print(
        f"{so.name:<8} {(so.partner_id.name or '')[:22]:<22} {so_total:>10.2f}  "
        f"{inv_names:<40} {inv_total:>10.2f}  {flag}"
    )
    print(f"{'':8} products: {prods}  invoice_status={so.invoice_status}  delivery={so.delivery_status}")

print()
print("=" * 90)
print("DRAFT INVOICES (no number yet)")
print("=" * 90)
for inv in draft_invs:
    sos = inv.invoice_line_ids.mapped("sale_line_ids.order_id")
    print(
        f"  id={inv.id}  name={inv.name or '/'}  partner={inv.partner_id.name}  "
        f"total={inv.amount_total}  SO={sos.mapped('name') or ['-']}"
    )
    for line in inv.invoice_line_ids:
        print(f"    line: {line.product_id.default_code}  {line.name[:45]}")

print()
print("=" * 90)
print("PROBLEM SUMMARY")
print("=" * 90)
for so in mismatch:
    print(f"  {so.name}  {so.partner_id.name}  SO=${so.amount_total}  invoices={so.invoice_ids.mapped('name')}")

# Ryan Kirby detail
print()
print("Ryan Kirby detail:")
for so in SO.search([("partner_id.name", "ilike", "Ryan Kirby"), ("state", "!=", "cancel")]):
    print(f"  {so.name}  total={so.amount_total}  inv={so.invoice_ids.mapped('name')}  lines:")
    for l in so.order_line:
        print(f"    {l.product_id.default_code}  qty={l.product_uom_qty}  invoiced={l.qty_invoiced}")

print()
print("Done.")
