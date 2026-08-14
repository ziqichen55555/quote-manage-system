# -*- coding: utf-8 -*-
"""Read-only: locate serial(s) matching *THG*."""
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SO = env["sale.order"].sudo()

print("=== SERIAL SEARCH *THG* (read-only) ===")
lots = Lot.search([("name", "ilike", "%THG%")], order="name")
print(f"matches: {len(lots)}")
for lot in lots:
    sku = lot.product_id.default_code or ""
    tmpl = lot.product_id.product_tmpl_id
    internal = sum(
        q.quantity
        for q in Quant.search(
            [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal")]
        )
    )
    orders = SO.search_count(
        [("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)]
    )
    print("\n" + "-" * 60)
    print(f"SN={lot.name!r} lot_id={lot.id} create={lot.create_date}")
    print(f"  product={sku!r} name={tmpl.name!r} on_hand={tmpl.qty_available}")
    print(f"  internal={internal:g} sale_orders={orders}")
    for q in Quant.search([("lot_id", "=", lot.id)]):
        print(
            f"  quant {q.location_id.complete_name} usage={q.location_id.usage} qty={q.quantity:g}"
        )
    mls = MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc")
    print(f"  move lines: {len(mls)}")
    for ml in mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        sale = ml.picking_id.sale_id.name if ml.picking_id and ml.picking_id.sale_id else ""
        print(
            f"    {ml.date} {ml.state} {ml.location_id.display_name}->{ml.location_dest_id.display_name} "
            f"qty={qty:g} sale={sale!r} pick={ml.picking_id.name if ml.picking_id else '-'}"
        )
    if internal > 0 and orders == 0:
        print("  => IN STOCK, no SO — same phantom pattern if missing physically")
    elif internal <= 0 and orders > 0:
        print("  => sold/shipped (ghost lot)")
print("\nDone.")
