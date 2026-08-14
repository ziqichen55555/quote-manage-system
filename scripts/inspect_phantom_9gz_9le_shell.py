# -*- coding: utf-8 -*-
"""Read-only: deep dive PC1PQ9GZ / PC1PQ9LE phantom stock."""
SERIALS = ["PC1PQ9GZ", "PC1PQ9LE"]
SKU_PREFIX = "20T1S6C300"

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
Move = env["stock.move"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)

print("=== PHANTOM CHECK:", ", ".join(SERIALS), "(read-only) ===")

for sn in SERIALS:
    print("\n" + "=" * 70)
    print("SERIAL:", sn)
    lots = Lot.search([("name", "=", sn)])
    if not lots:
        print("  NOT FOUND in stock.lot")
        continue
    for lot in lots:
        sku = lot.product_id.default_code or ""
        tmpl = lot.product_id.product_tmpl_id
        print(f"  lot_id={lot.id} product={sku!r} tmpl_id={tmpl.id}")
        print(
            f"  tmpl active={tmpl.active} published={tmpl.website_published} "
            f"sale_ok={tmpl.sale_ok} on_hand={tmpl.qty_available}"
        )

        all_quants = Quant.search([("lot_id", "=", lot.id)])
        print(f"  all quants ({len(all_quants)}):")
        wh_plus = 0.0
        for q in all_quants:
            print(
                f"    id={q.id} loc={q.location_id.complete_name} usage={q.location_id.usage} "
                f"qty={q.quantity:g} reserved={q.reserved_quantity:g} in_date={q.in_date}"
            )
            if q.location_id.usage == "internal" and q.quantity > 0:
                wh_plus += q.quantity

        print(f"  => net internal on-hand for this SN: {wh_plus:g}")
        print(f"  => counted in website bucket on_hand: {tmpl.qty_available:g}")

        mls = MoveLine.search([("lot_id", "=", lot.id)], order="id desc", limit=15)
        print(f"  move lines (latest {len(mls)}):")
        for ml in mls:
            qty = getattr(ml, "qty_done", None) or ml.quantity
            pick = ml.picking_id.name if ml.picking_id else "-"
            print(
                f"    id={ml.id} state={ml.state} date={ml.date} pick={pick} "
                f"{ml.location_id.display_name} -> {ml.location_dest_id.display_name} "
                f"qty={qty:g} origin={ml.picking_id.origin or ''}"
            )

        moves = Move.search([("lot_ids", "in", lot.id)], order="id desc", limit=10)
        if moves:
            print(f"  stock moves referencing lot ({len(moves)}):")
            for m in moves:
                print(
                    f"    id={m.id} state={m.state} {m.location_id.display_name} -> "
                    f"{m.location_dest_id.display_name} qty={m.product_uom_qty:g} "
                    f"origin={m.origin or ''} pick={m.picking_id.name if m.picking_id else '-'}"
                )

print("\n" + "=" * 70)
print("T1S6C300 CMOSP buckets — serials with lot but internal qty=0")
for code in ["20T1S6C300-BT70-CMOSP", "20T1S6C300-BTU70-CMOSP"]:
    tmpl = PT.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        continue
    variant = tmpl.product_variant_ids[:1]
    lots = Lot.search([("product_id", "=", variant.id)])
    ghost = []
    live = []
    for lot in lots:
        internal = sum(
            q.quantity
            for q in Quant.search([("lot_id", "=", lot.id), ("location_id.usage", "=", "internal")])
        )
        if internal > 0:
            live.append((lot.name, internal))
        else:
            ghost.append(lot.name)
    print(f"\n{code}: on_hand={tmpl.qty_available} lots={len(lots)} internal>0={len(live)} ghost_lots={len(ghost)}")
    for name, qty in sorted(live):
        flag = " <-- USER REPORTS MISSING" if name in SERIALS else ""
        print(f"  IN STOCK: {name} qty={qty:g}{flag}")
    if ghost:
        print(f"  GHOST (lot only): {', '.join(sorted(ghost)[:20])}")
        if len(ghost) > 20:
            print(f"    ... +{len(ghost)-20} more")

print("\nDone.")
