# -*- coding: utf-8 -*-
"""Read-only: find *3P5*/*417* serials anywhere + T1S6C300 phantom candidates."""
PATTERNS = ["%3P5%", "%417%", "%9J5%", "%9HZ%", "%9M8%"]
SKU = "20T1S6C300"

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
SO = env["sale.order"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)

print("=== BROAD SERIAL SEARCH (read-only) ===")

for pat in PATTERNS:
    lots = Lot.search([("name", "ilike", pat)], order="name")
    print(f"\n--- ilike {pat!r}: {len(lots)} lot(s) ---")
    for lot in lots[:30]:
        internal = sum(
            q.quantity
            for q in Quant.search(
                [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal")]
            )
        )
        orders = SO.search_count(
            [("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)]
        )
        print(
            f"  {lot.name} product={lot.product_id.default_code} internal={internal:g} "
            f"orders={orders} create={lot.create_date}"
        )
    if len(lots) > 30:
        print(f"  ... +{len(lots)-30} more")

print("\n" + "=" * 70)
print(f"ALL {SKU} *-CMOSP in WH with zero sale orders")
for code in [f"{SKU}-BT70-CMOSP", f"{SKU}-BTU70-CMOSP"]:
    tmpl = PT.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        continue
    variant = tmpl.product_variant_ids[:1]
    print(f"\n{code} on_hand={tmpl.qty_available}")
    for lot in Lot.search([("product_id", "=", variant.id)], order="name"):
        internal = sum(
            q.quantity
            for q in Quant.search(
                [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal")]
            )
        )
        if internal <= 0:
            continue
        orders = SO.search_count(
            [("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)]
        )
        if orders == 0:
            print(f"  {lot.name} internal={internal:g} orders=0 create={lot.create_date}")

print("\nDone.")
