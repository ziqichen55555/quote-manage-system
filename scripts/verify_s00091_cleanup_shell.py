# -*- coding: utf-8 -*-
"""Read-only: confirm S00091 cleanup after manual cancel."""
SaleOrder = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()
Product = env["product.product"].sudo()

so = SaleOrder.search([("name", "=", "S00091")], limit=1)
assert so.exists(), "S00091 not found"
prod = Product.search([("default_code", "=", "S22A450BW")], limit=1)

print("=== S00091 ===")
print(f"state={so.state} invoice_status={so.invoice_status}")
print(f"qty_delivered: {[(l.product_id.default_code, l.qty_delivered) for l in so.order_line]}")
print(f"invoices: {[(i.name, i.state, i.payment_state) for i in so.invoice_ids]}")

pickings = Picking.search([
    "|", ("sale_id", "=", so.id),
    ("origin", "ilike", "S00091"),
], order="id")
named = Picking.search([
    ("name", "in", ["WH/OUT/00071", "WH/IN/00003", "WH/OUT/00075", "WH/IN/00005"])
], order="id")
pickings |= named

print("\n=== Transfers ===")
for p in pickings.sorted("id"):
    print(
        f"{p.name} state={p.state:10} "
        f"{p.location_id.complete_name} -> {p.location_dest_id.complete_name} "
        f"origin={p.origin!r}"
    )

open_p = pickings.filtered(lambda p: p.state not in ("done", "cancel"))
print(f"\nOpen pickings (should be none): {[(p.name, p.state) for p in open_p]}")

print(f"\n=== S22A450BW stock ===")
print(f"qty_available={prod.qty_available} virtual={prod.virtual_available}")

print("\n=== Verdict ===")
checks = {
    "SO cancelled": so.state == "cancel",
    "No open pickings": not open_p,
    "Invoice cancelled": all(i.state == "cancel" for i in so.invoice_ids),
    "No payment": all(i.payment_state in ("not_paid", False) for i in so.invoice_ids),
    "qty_delivered zero": all(l.qty_delivered == 0 for l in so.order_line),
}
for k, ok in checks.items():
    print(f"  {'OK' if ok else 'FAIL'}: {k}")
print("ALL_OK:", all(checks.values()))
