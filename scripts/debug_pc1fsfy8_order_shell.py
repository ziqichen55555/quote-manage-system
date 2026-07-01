# -*- coding: utf-8 -*-
"""Diagnose PC1FSFY8 on sale order 00029."""
SERIAL = "PC1FSFY8"
ORDER_NAME = "S00013"

Lot = env["stock.lot"].sudo()
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SaleOrder = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()
Importer = env["product.csv.importer"].sudo()

print("=" * 60)
print(f"SERIAL: {SERIAL} | ORDER: {ORDER_NAME}")
print("=" * 60)

# --- Lot records ---
lots = Lot.search([("name", "=ilike", SERIAL)])
print(f"\nLOT RECORDS: {len(lots)}")
for lot in lots:
    tmpl = lot.product_id.product_tmpl_id
    quants = Quant.search(
        [
            ("lot_id", "=", lot.id),
            ("quantity", "!=", 0),
        ]
    )
    print(
        f"  lot_id={lot.id} product={lot.product_id.display_name!r} "
        f"variant_code={lot.product_id.default_code!r} tmpl_tracking={tmpl.tracking}"
    )
    for q in quants:
        print(
            f"    quant: loc={q.location_id.complete_name!r} qty={q.quantity} "
            f"reserved={q.reserved_quantity} available={q.quantity - q.reserved_quantity}"
        )

# --- Delivered check ---
if hasattr(Importer, "_serial_is_delivered"):
    for lot in lots:
        delivered = Importer._serial_is_delivered(lot.name, lot.product_id.id)
        print(f"  _serial_is_delivered({lot.name}, {lot.product_id.id}) = {delivered}")

# --- Done customer moves for this serial ---
done_moves = MoveLine.search(
    [
        ("lot_id", "in", lots.ids),
        ("state", "=", "done"),
    ]
)
print(f"\nDONE MOVE LINES for serial: {len(done_moves)}")
for ml in done_moves[:10]:
    print(
        f"  picking={ml.picking_id.name!r} order={ml.picking_id.sale_id.name!r} "
        f"from={ml.location_id.usage} to={ml.location_dest_id.usage} qty={ml.quantity}"
    )

# --- Open reservations ---
open_lines = MoveLine.search(
    [
        ("lot_id", "in", lots.ids),
        ("state", "not in", ["done", "cancel"]),
    ]
)
print(f"\nOPEN/RESERVED MOVE LINES for serial: {len(open_lines)}")
for ml in open_lines:
    print(
        f"  picking={ml.picking_id.name!r} order={ml.picking_id.sale_id.name!r} "
        f"state={ml.state} qty={ml.quantity} product={ml.product_id.default_code!r}"
    )

# --- Sale order 00029 ---
order = SaleOrder.search([("name", "=", ORDER_NAME)], limit=1)
if not order:
    order = SaleOrder.search([("name", "ilike", ORDER_NAME)], limit=1)
print(f"\nSALE ORDER: {order.name if order else 'NOT FOUND'} id={order.id if order else '-'} state={order.state if order else '-'}")
if order:
    for line in order.order_line:
        if line.product_id.type != "product":
            continue
        print(
            f"  line: {line.product_id.display_name!r} code={line.product_id.default_code!r} "
            f"qty={line.product_uom_qty} delivered={line.qty_delivered}"
        )
    pickings = order.picking_ids
    print(f"  pickings: {len(pickings)}")
    for p in pickings:
        print(f"    {p.name} type={p.picking_type_code} state={p.state}")
        for move in p.move_ids:
            print(
                f"      move product={move.product_id.default_code!r} "
                f"demand={move.product_uom_qty} reserved={move.quantity} state={move.state}"
            )
            for ml in move.move_line_ids:
                print(
                    f"        ml: lot={ml.lot_id.name if ml.lot_id else ml.lot_name!r} "
                    f"qty={ml.quantity} state={ml.state}"
                )

# --- Match order line product vs lot product ---
if order and lots:
    order_products = order.order_line.mapped("product_id")
    lot_products = lots.mapped("product_id")
    print(f"\nPRODUCT MATCH:")
    print(f"  order line product ids: {order_products.ids}")
    print(f"  lot product ids: {lot_products.ids}")
    print(f"  overlap: {set(order_products.ids) & set(lot_products.ids)}")

# --- SKU snapshot for T490s ---
for sku in ("20NYS4CP00", "20NYS4CP00-8G-256G-N", "20NYS4CP00-8G-256G-T"):
    if hasattr(Importer, "_serial_stock_snapshot"):
        snap = Importer._serial_stock_snapshot(sku)
        if snap.get("found"):
            has_sn = SERIAL.upper() in [s.upper() for s in (snap.get("lots_in_stock") or [])]
            print(
                f"\nSNAPSHOT {sku}: on_hand={snap['on_hand']} "
                f"no_lot_qty={snap.get('no_lot_qty')} "
                f"has_{SERIAL}={has_sn}"
            )
            if has_sn:
                print(f"  lots_in_stock count={len(snap['lots_in_stock'])}")
