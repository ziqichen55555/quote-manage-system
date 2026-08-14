# -*- coding: utf-8 -*-
"""Read-only: locate PC1PQ9GZ / PC1PQ9LG for 20T1S6C300."""
SERIALS = ["PC1PQ9GZ", "PC1PQ9LG"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)


def print_lot(lot):
    sku = lot.product_id.default_code or ""
    tmpl = lot.product_id.product_tmpl_id
    print(f"  SN={lot.name!r} lot_id={lot.id}")
    print(
        f"    product={sku!r} tmpl={tmpl.default_code!r} "
        f"active={tmpl.active} published={tmpl.website_published} "
        f"sale_ok={tmpl.sale_ok} tmpl_on_hand={tmpl.qty_available}"
    )
    quants = Quant.search([("lot_id", "=", lot.id)])
    internal = 0.0
    for q in quants:
        print(
            f"    quant id={q.id} loc={q.location_id.complete_name} usage={q.location_id.usage} "
            f"qty={q.quantity:g} reserved={q.reserved_quantity:g}"
        )
        if q.location_id.usage == "internal":
            internal += q.quantity
    print(f"    => net internal qty for this SN: {internal:g}")

    mls = MoveLine.search([("lot_id", "=", lot.id)], order="id desc", limit=8)
    if mls:
        print("    recent move lines:")
        for ml in mls:
            qty = getattr(ml, "qty_done", None) or ml.quantity
            pick = ml.picking_id.name if ml.picking_id else "-"
            print(
                f"      state={ml.state} {ml.date} {pick} "
                f"{ml.location_id.display_name} -> {ml.location_dest_id.display_name} qty={qty:g}"
            )


print("=== Locate PC1PQ9GZ / PC1PQ9LG (read-only) ===")
for sn in SERIALS:
    print(f"\n--- {sn} ---")
    lots = Lot.search([("name", "=", sn)])
    if not lots:
        # fuzzy fallback
        lots = Lot.search([("name", "ilike", sn[-3:]), ("product_id.default_code", "ilike", "T1S6C300")])
        if lots:
            print(f"  exact not found; fuzzy matches for *{sn[-3:]}* on T1S6C300:")
        else:
            print("  (not found)")
            continue
    for lot in lots:
        print_lot(lot)

print("\nDone.")
