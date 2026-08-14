# -*- coding: utf-8 -*-
"""Read-only: trace T1S6C300 serials matching *3P5* / *417* (+ recap 9GZ/9LG)."""
PATTERNS = ["%3P5%", "%417%"]
RECAP = ["PC1PQ9GZ", "PC1PQ9LG"]
SKU_HINT = "T1S6C300"

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SO = env["sale.order"].sudo()

print("=== TRACE T1S6C300 serials *3P5* / *417* (read-only) ===")


def report_lot(lot):
    sku = lot.product_id.default_code or ""
    tmpl = lot.product_id.product_tmpl_id
    print(f"\n  SN={lot.name!r} lot_id={lot.id} create={lot.create_date}")
    print(f"    product={sku!r} tmpl_on_hand={tmpl.qty_available}")

    internal = 0.0
    for q in Quant.search([("lot_id", "=", lot.id)]):
        print(
            f"    quant id={q.id} loc={q.location_id.complete_name} usage={q.location_id.usage} "
            f"qty={q.quantity:g} reserved={q.reserved_quantity:g} in_date={q.in_date}"
        )
        if q.location_id.usage == "internal":
            internal += q.quantity
    print(f"    => net internal: {internal:g}")

    mls = MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc")
    print(f"    move lines: {len(mls)}")
    for ml in mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        pick = ml.picking_id.name if ml.picking_id else "-"
        ptype = ml.picking_id.picking_type_id.code if ml.picking_id and ml.picking_id.picking_type_id else "?"
        sale = ml.picking_id.sale_id.name if ml.picking_id and ml.picking_id.sale_id else ""
        print(
            f"      {ml.date} state={ml.state} type={ptype} pick={pick} sale={sale!r} "
            f"{ml.location_id.display_name} -> {ml.location_dest_id.display_name} qty={qty:g}"
        )

    outbound = mls.filtered(
        lambda ml: ml.state == "done"
        and ml.location_id.usage == "internal"
        and ml.location_dest_id.usage == "customer"
    )
    orders = SO.search([("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)])
    print(f"    sale orders: {len(orders)}")
    for o in orders:
        print(f"      {o.name} state={o.state} partner={o.partner_id.display_name}")
    if internal > 0 and not outbound and not orders:
        print("    => IN STOCK in Odoo, never shipped, no SO — phantom if missing physically")
    elif outbound:
        print("    => had outbound move(s)")
    elif internal <= 0:
        print("    => no internal stock now")


for sn in RECAP:
    print("\n" + "#" * 60)
    print(f"# RECAP {sn}")
    lots = Lot.search([("name", "=", sn)])
    if not lots:
        print("  not found")
        continue
    for lot in lots:
        if SKU_HINT.upper() not in (lot.product_id.default_code or "").upper():
            continue
        report_lot(lot)

for pat in PATTERNS:
    print("\n" + "#" * 60)
    print(f"# pattern ilike {pat!r}")
    lots = Lot.search([("name", "ilike", pat)], order="name")
    matched = [l for l in lots if SKU_HINT.upper() in (l.product_id.default_code or "").upper()]
    if not matched:
        print("  (none on T1S6C300 SKUs)")
        continue
    for lot in matched:
        report_lot(lot)

print("\nDone.")
