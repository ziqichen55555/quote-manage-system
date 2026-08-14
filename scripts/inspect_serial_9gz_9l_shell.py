# -*- coding: utf-8 -*-
"""Read-only: locate PC1PQ9GZ / PC1PQ9LE for 20T1S6C300."""
SERIALS = ["PC1PQ9GZ", "PC1PQ9LE"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
SO = env["sale.order"].sudo()


def print_lot(lot):
    sku = lot.product_id.default_code or ""
    tmpl = lot.product_id.product_tmpl_id
    print(f"  SN={lot.name!r} lot_id={lot.id}")
    print(
        f"    product={sku!r} tmpl={tmpl.default_code!r} "
        f"active={tmpl.active} published={tmpl.website_published} "
        f"sale_ok={tmpl.sale_ok}"
    )
    quants = Quant.search(
        [("lot_id", "=", lot.id), "|", ("quantity", "!=", 0), ("reserved_quantity", "!=", 0)]
    )
    if quants:
        for q in quants:
            print(
                f"    quant loc={q.location_id.complete_name} usage={q.location_id.usage} "
                f"qty={q.quantity:g} reserved={q.reserved_quantity:g}"
            )
    else:
        print("    quant: (no nonzero quant on this lot)")

    mls = MoveLine.search(
        [("lot_id", "=", lot.id), ("state", "=", "done")],
        order="date desc",
        limit=5,
    )
    if mls:
        print("    recent done move lines:")
        for ml in mls:
            picking = ml.picking_id.name if ml.picking_id else "(no picking)"
            qty = getattr(ml, "qty_done", None) or ml.quantity
            print(
                f"      {ml.date} {picking} {ml.location_id.display_name} -> "
                f"{ml.location_dest_id.display_name} qty={qty:g} "
                f"origin={ml.picking_id.origin or ''}"
            )

    open_orders = SO.search(
        [
            ("order_line.move_ids.move_line_ids.lot_id", "=", lot.id),
            ("state", "in", ("draft", "sent", "sale")),
        ],
        limit=5,
    )
    if open_orders:
        print("    open sale orders:")
        for o in open_orders:
            print(f"      {o.name} state={o.state} website={bool(o.website_id)}")


print("=== Locate PC1PQ9GZ / PC1PQ9LE (read-only) ===")
for sn in SERIALS:
    print(f"\n--- {sn} ---")
    lots = Lot.search([("name", "=", sn)])
    if not lots:
        print("  (not found)")
        continue
    for lot in lots:
        print_lot(lot)

print("\nDone.")
