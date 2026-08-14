# -*- coding: utf-8 -*-
"""Read-only: reconcile 20WNA07YAU-BT70-CMOSP serials TKM/TMP/TLW/TJA/THG."""
SKU = "20WNA07YAU-BT70-CMOSP"
SERIALS = ["GM048TKM", "GM048TMP", "GM048TLW", "GM048TJA", "GM048THG"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SO = env["sale.order"].sudo()
SOL = env["sale.order.line"].sudo()
PT = env["product.template"].sudo()

print(f"=== {SKU} serial reconcile (read-only) ===")
tmpl = PT.search([("default_code", "=", SKU)], limit=1)
print(f"tmpl on_hand={tmpl.qty_available} free_qty={getattr(tmpl,'free_qty',None)}")

for sn in SERIALS:
    print("\n" + "-" * 60)
    lot = Lot.search([("name", "=", sn), ("product_id.product_tmpl_id", "=", tmpl.id)], limit=1)
    if not lot:
        lot = Lot.search([("name", "=", sn)], limit=1)
    if not lot:
        print(f"{sn}: NOT FOUND")
        continue
    print(f"{sn} lot_id={lot.id} product={lot.product_id.default_code}")
    internal = 0.0
    reserved = 0.0
    for q in Quant.search([("lot_id", "=", lot.id)]):
        print(
            f"  quant id={q.id} {q.location_id.complete_name} usage={q.location_id.usage} "
            f"qty={q.quantity:g} reserved={q.reserved_quantity:g} "
            f"inv_qty={getattr(q,'inventory_quantity',None)}"
        )
        if q.location_id.usage == "internal":
            internal += q.quantity
            reserved += q.reserved_quantity
    print(f"  => internal={internal:g} reserved={reserved:g} available={internal-reserved:g}")

    # open reservations
    for q in Quant.search(
        [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal"), ("reserved_quantity", ">", 0)]
    ):
        print(f"  RESERVED on {q.location_id.complete_name}: {q.reserved_quantity:g}")

    mls = MoveLine.search([("lot_id", "=", lot.id)], order="date desc, id desc", limit=5)
    for ml in mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        sale = ml.picking_id.sale_id.name if ml.picking_id and ml.picking_id.sale_id else ""
        print(
            f"  move {ml.date} {ml.state} {ml.location_id.display_name}->{ml.location_dest_id.display_name} "
            f"qty={qty:g} sale={sale!r} pick={ml.picking_id.name if ml.picking_id else '-'}"
        )

    orders = SO.search([("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)], order="id desc")
    for o in orders[:3]:
        print(f"  SO {o.name} state={o.state} partner={o.partner_id.display_name}")

# open pickings reserving this product
variant = tmpl.product_variant_ids[:1]
open_moves = env["stock.move"].sudo().search(
    [
        ("product_id", "=", variant.id),
        ("state", "in", ("waiting", "confirmed", "assigned", "partially_available")),
    ]
)
print("\n" + "=" * 60)
print(f"OPEN stock moves for {SKU}: {len(open_moves)}")
for m in open_moves:
    sns = m.move_line_ids.filtered(lambda ml: ml.lot_id).mapped("lot_id.name")
    print(
        f"  {m.picking_id.name if m.picking_id else '-'} state={m.state} "
        f"qty={m.product_uom_qty:g} reserved={m.quantity:g} origin={m.origin or ''} serials={sns}"
    )

print("\nDone.")
