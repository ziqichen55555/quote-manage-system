# -*- coding: utf-8 -*-
"""Read-only: trace PC27R3P5 / PC27R417 (3P5 / 417)."""
SERIALS = ["PC27R3P5", "PC27R417"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SO = env["sale.order"].sudo()

for sn in SERIALS:
    print("\n" + "=" * 60)
    print(sn)
    lot = Lot.search([("name", "=", sn)], limit=1)
    if not lot:
        print("NOT FOUND")
        continue
    print(f"product={lot.product_id.default_code} create={lot.create_date}")
    for q in Quant.search([("lot_id", "=", lot.id)]):
        print(f"  {q.location_id.complete_name} usage={q.location_id.usage} qty={q.quantity:g}")
    for ml in MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc"):
        qty = getattr(ml, "qty_done", None) or ml.quantity
        sale = ml.picking_id.sale_id.name if ml.picking_id and ml.picking_id.sale_id else ""
        print(
            f"  {ml.date} {ml.state} {ml.location_id.display_name}->{ml.location_dest_id.display_name} "
            f"qty={qty:g} sale={sale!r} pick={ml.picking_id.name if ml.picking_id else '-'}"
        )
    print(f"  sale orders: {SO.search_count([('order_line.move_ids.move_line_ids.lot_id','=',lot.id)])}")
print("\nDone.")
