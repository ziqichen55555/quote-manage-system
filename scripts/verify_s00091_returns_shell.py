# -*- coding: utf-8 -*-
"""Read-only: verify S00091 transfer chain + net stock for S22A450BW."""
Picking = env["stock.picking"].sudo()
SaleOrder = env["sale.order"].sudo()
Product = env["product.product"].sudo()

so = SaleOrder.search([("name", "=", "S00091")], limit=1)
prod = Product.search([("default_code", "=", "S22A450BW")], limit=1)

print("=== S00091 ===")
print(f"state={so.state} invoice_status={so.invoice_status}")
print(f"qty_delivered on lines: {[(l.product_id.default_code, l.qty_delivered) for l in so.order_line]}")
inv = so.invoice_ids
print(f"invoices: {[(i.name, i.state, i.payment_state) for i in inv]}")

print("\n=== All pickings linked to S00091 (by origin/sale) ===")
pickings = Picking.search([
    "|", "|",
    ("sale_id", "=", so.id),
    ("origin", "ilike", "S00091"),
    ("origin", "ilike", "WH/OUT/00071"),
], order="id")
# also explicit names from user
named = Picking.search([("name", "in", ["WH/OUT/00071", "WH/IN/00003", "WH/OUT/00075", "WH/IN/00005"])], order="id")
pickings |= named

for p in pickings.sorted("id"):
    print(
        f"{p.name} state={p.state:10} "
        f"{p.location_id.complete_name} -> {p.location_dest_id.complete_name} "
        f"origin={p.origin!r} date_done={p.date_done}"
    )
    for m in p.move_ids:
        qty = m.quantity if "quantity" in m._fields else m.product_uom_qty
        print(
            f"  move {m.product_id.default_code} demand={m.product_uom_qty} "
            f"qty={qty} state={m.state}"
        )

print("\n=== Net effect for S22A450BW on these pickings (done only) ===")
# +1 when dest is internal stock, -1 when src is stock to customer
net = 0.0
for p in pickings.sorted("id"):
    if p.state != "done":
        print(f"  SKIP not-done {p.name}")
        continue
    for m in p.move_ids.filtered(lambda x: x.product_id == prod):
        qty = m.quantity if "quantity" in m._fields else m.product_uom_qty
        src_usage = m.location_id.usage
        dest_usage = m.location_dest_id.usage
        delta = 0.0
        if src_usage == "internal" and dest_usage == "customer":
            delta = -qty
        elif src_usage == "customer" and dest_usage == "internal":
            delta = +qty
        net += delta
        print(f"  {p.name}: delta={delta:+} (src={m.location_id.complete_name} dest={m.location_dest_id.complete_name})")
print(f"NET stock change from this chain: {net:+} (want 0 if fully returned)")

print(f"\n=== Product qty now ===")
print(f"S22A450BW qty_available={prod.qty_available} virtual={prod.virtual_available}")
# quants in WH/Stock
Quant = env["stock.quant"].sudo()
stock_loc = env.ref("stock.stock_location_stock", raise_if_not_found=False)
wh_stock = env["stock.location"].sudo().search([("complete_name", "=", "WH/Stock")], limit=1)
loc = wh_stock or stock_loc
quants = Quant.search([("product_id", "=", prod.id), ("location_id", "child_of", loc.id)])
print(f"quants under {loc.complete_name}: {sum(quants.mapped('quantity'))} (reserved {sum(quants.mapped('reserved_quantity'))})")

print("\n=== Verdict ===")
open_p = pickings.filtered(lambda p: p.state not in ("done", "cancel"))
print(f"open/draft pickings: {[(p.name, p.state) for p in open_p]}")
if net == 0 and so.state == "cancel":
    print("OK: stock net zero and SO cancelled")
elif net == 0 and so.state != "cancel":
    print("STOCK OK (net 0). Still need: cancel/reset invoice + cancel SO if not done.")
elif net < 0:
    print("STILL SHORT stock — another return needed or validate pending IN")
elif net > 0:
    print("OVER-returned — too many returns validated; investigate OUT/00075")
