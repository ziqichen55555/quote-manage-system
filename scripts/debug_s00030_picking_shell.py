# -*- coding: utf-8 -*-
"""Full trace: INV/2026/00007 vs S00030 vs WH/OUT pickings."""
refs = {
    "invoice": "INV/2026/00007",
    "order": "S00030",
    "picking": "WH/OUT/00032",
}

Move = env["account.move"].sudo()
SO = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()

inv = Move.search([("name", "=", refs["invoice"])], limit=1)
so = SO.search([("name", "=", refs["order"])], limit=1)
pick32 = Picking.search([("name", "=", refs["picking"])], limit=1)

print("=" * 72)
print("INVOICE", refs["invoice"])
if inv:
    print(f"  partner={inv.partner_id.name}  total={inv.amount_total}  state={inv.state}")
    for line in inv.invoice_line_ids:
        p = line.product_id
        print(
            f"  inv line: product_id={p.id}  code={p.default_code!r}  "
            f"name={line.name[:55]}  qty={line.quantity}"
        )
    sos = inv.invoice_line_ids.mapped("sale_line_ids.order_id")
    print(f"  linked SO from invoice lines: {sos.mapped('name')}")
else:
    print("  NOT FOUND")

print()
print("=" * 72)
print("SALE ORDER", refs["order"])
if so:
    print(f"  partner={so.partner_id.name}  state={so.state}  delivery={so.delivery_status}")
    print(f"  invoice_ids: {so.invoice_ids.mapped('name')}")
    for line in so.order_line:
        p = line.product_id
        print(
            f"  SO line id={line.id}: product_id={p.id}  code={p.default_code!r}  "
            f"name={line.name[:55]}  qty={line.product_uom_qty}  invoiced={line.qty_invoiced}  delivered={line.qty_delivered}"
        )
    print("  ALL pickings on this SO:")
    for p in so.picking_ids.sorted("name"):
        prods = p.move_ids.mapped("product_id.default_code")
        serials = p.move_line_ids.filtered(lambda ml: ml.lot_id).mapped("lot_id.name")
        print(
            f"    {p.name}  state={p.state}  products={prods}  serials={serials}"
        )
else:
    print("  NOT FOUND")

print()
print("=" * 72)
print("PICKING", refs["picking"])
if pick32:
    so_from_pick = pick32.sale_id
    print(f"  state={pick32.state}  partner={pick32.partner_id.name}")
    print(f"  sale_id={so_from_pick.name if so_from_pick else 'NONE'}")
    print(f"  origin={pick32.origin!r}")
    for move in pick32.move_ids:
        p = move.product_id
        print(
            f"  move: product_id={p.id}  code={p.default_code!r}  "
            f"name={p.display_name[:55]}  demand={move.product_uom_qty}  done={move.quantity}"
        )
    for ml in pick32.move_line_ids:
        sn = ml.lot_id.name if ml.lot_id else "-"
        print(
            f"  move line: product={ml.product_id.default_code!r}  serial={sn}  qty={ml.quantity}"
        )
else:
    print("  NOT FOUND")

# Any other open pickings for Latitude 3301
print()
print("=" * 72)
print("Open outgoing pickings with LATITUDE 3301:")
PT = env["product.product"].sudo()
lat = PT.search([("default_code", "ilike", "LATITUDE 3301")], limit=5)
for p in lat:
    open_picks = Picking.search(
        [
            ("state", "in", ("assigned", "confirmed", "waiting")),
            ("move_ids.product_id", "=", p.id),
        ]
    )
    for op in open_picks:
        serials = op.move_line_ids.filtered(lambda ml: ml.lot_id).mapped("lot_id.name")
        print(f"  {op.name}  SO={op.sale_id.name if op.sale_id else '-'}  state={op.state}  serials={serials}")

print()
print("Done.")
