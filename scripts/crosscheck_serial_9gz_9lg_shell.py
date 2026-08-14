# -*- coding: utf-8 -*-
"""Read-only: cross-check PC1PQ9GZ / PC1PQ9LG across all products + quants."""
SERIALS = ["PC1PQ9GZ", "PC1PQ9LG"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()

print("=== CROSS-PRODUCT SERIAL CHECK ===")
for sn in SERIALS:
    print(f"\n--- {sn} ---")
    lots = Lot.search([("name", "=", sn)])
    print(f"lot records: {len(lots)}")
    for lot in lots:
        print(f"  lot={lot.id} product={lot.product_id.default_code} create={lot.create_date}")
        for q in Quant.search([("lot_id", "=", lot.id)]):
            print(
                f"    q={q.id} {q.location_id.complete_name} usage={q.location_id.usage} "
                f"qty={q.quantity:g} in_date={q.in_date} write={q.write_date}"
            )
    # move lines without lot filter but product T1S6C300 around import date
    mls = MoveLine.search(
        [
            ("product_id.default_code", "ilike", "20T1S6C300%"),
            ("date", ">=", "2026-07-01"),
            ("date", "<=", "2026-07-10"),
        ],
        order="date asc, id asc",
        limit=200,
    )
    tagged = mls.filtered(lambda ml: ml.lot_id and ml.lot_id.name == sn)
    print(f"  move lines with this lot_id in Jul-2026 T1S6C300 window: {len(tagged)}")
    for ml in tagged:
        print(
            f"    {ml.date} ml={ml.id} {ml.location_id.display_name}->{ml.location_dest_id.display_name} "
            f"qty={getattr(ml,'qty_done',None) or ml.quantity} pick={ml.picking_id.name if ml.picking_id else '-'}"
        )

print("\nDone.")
