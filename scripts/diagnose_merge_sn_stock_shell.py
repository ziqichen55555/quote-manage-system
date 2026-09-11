# -*- coding: utf-8 -*-
"""Diagnose SN/lot placement after merge restore (read-only)."""
PT = env["product.template"].sudo().with_context(active_test=False)
PP = env["product.product"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo().with_context(active_test=False)

WRONG_IDS = list(range(929, 938))
WRONG_TO_RIGHT = {
    929: 828,   # 20L8SBL100
    930: 862,   # 20L8SDCE00 BTU70
    931: 831,   # 20NYS4CP00 256G BT70
    932: 835,   # 20NYS4CP00 512G BT70
    933: 863,   # 20T0003UAU
    934: 844,   # 20WN0025AU
    935: 846,   # 20WNA07YAU
    936: 867,   # 20WNS1M500
    937: 870,   # 20WNS6LL00
}

wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
stock_loc = wh.lot_stock_id if wh else None

print("=" * 72)
print("MERGE SN STOCK DIAGNOSIS (read-only)")
print("=" * 72)

active_all = PT.search_count([("active", "=", True)])
active_sale = PT.search_count([("active", "=", True), ("sale_ok", "=", True)])
print(f"\nActive templates (all): {active_all}")
print(f"Active + sale_ok (UI list): {active_sale}")

print("\n--- Wrong archived products (929-937) ---")
wrong_lot_total = 0
wrong_qty_total = 0
for wid in WRONG_IDS:
    tmpl = PT.browse(wid)
    if not tmpl.exists():
        print(f"ID {wid}: MISSING")
        continue
    variant = tmpl.product_variant_ids[:1]
    lots = Lot.search([("product_id", "=", variant.id)])
    qty = float(tmpl.qty_available or 0)
    nonzero = Quant.search_count([
        ("product_id", "=", variant.id),
        ("quantity", "!=", 0),
    ] + ([("location_id", "child_of", stock_loc.id)] if stock_loc else []))
    wrong_lot_total += len(lots)
    wrong_qty_total += qty
    print(
        f"ID={wid} active={tmpl.active} ref={tmpl.default_code} "
        f"on_hand={qty:g} lots={len(lots)} nonzero_quants={nonzero}"
    )
    for lot in lots[:5]:
        q = Quant.search([
            ("lot_id", "=", lot.id),
            ("product_id", "=", variant.id),
        ], limit=3)
        qinfo = ", ".join(f"loc={x.location_id.display_name} qty={x.quantity:g}" for x in q)
        print(f"    lot {lot.name}: {qinfo or 'no quants'}")
    if len(lots) > 5:
        print(f"    ... {len(lots) - 5} more lots")

print(f"\nWrong products: {len(WRONG_IDS)} templates, {wrong_lot_total} lots, on_hand sum={wrong_qty_total:g}")

print("\n--- Target restored products ---")
need_restore = 0
for wid, rid in WRONG_TO_RIGHT.items():
    wrong = PT.browse(wid)
    right = PT.browse(rid)
    if not wrong.exists() or not right.exists():
        print(f"{wid}->{rid}: MISSING")
        continue
    wvar = wrong.product_variant_ids[:1]
    rvar = right.product_variant_ids[:1]
    w_lots = Lot.search([("product_id", "=", wvar.id)])
    r_on = float(right.qty_available or 0)
    missing_on_right = 0
    for lot in w_lots:
        on_right = Quant.search_count([
            ("product_id", "=", rvar.id),
            ("lot_id.name", "=", lot.name),
            ("quantity", ">", 0),
        ])
        if not on_right:
            missing_on_right += 1
    need_restore += missing_on_right
    print(
        f"{wid} {wrong.default_code}\n"
        f"  -> {rid} {right.default_code} active={right.active} "
        f"on_hand={r_on:g} wrong_lots={len(w_lots)} missing_on_right={missing_on_right}"
    )

print(f"\nLots to move back (approx): {need_restore}")
print("\nDone (no changes).")
