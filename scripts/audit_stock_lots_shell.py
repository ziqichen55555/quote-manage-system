# -*- coding: utf-8 -*-
"""Report stock.lot inventory on production after fresh import."""
from collections import defaultdict

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)

lots = Lot.search([("company_id", "=", env.company.id)])
print(f"Total stock.lot records: {len(lots)}")

active_lots = Lot.search([("company_id", "=", env.company.id), ("product_id.active", "=", True)])
inactive_lots = len(lots) - len(active_lots)
print(f"Lots on active products: {len(active_lots)}")
print(f"Lots on inactive/archived products: {inactive_lots}")

with_stock = 0
without_stock = 0
by_serial = defaultdict(list)
for lot in lots:
    qty = sum(
        Quant.search(
            [
                ("lot_id", "=", lot.id),
                ("location_id.usage", "=", "internal"),
                ("quantity", ">", 0),
            ]
        ).mapped("quantity")
    )
    if qty > 0:
        with_stock += 1
    else:
        without_stock += 1
    sn = (lot.name or "").strip().upper()
    if sn:
        tmpl = lot.product_id.product_tmpl_id
        by_serial[sn].append(
            {
                "lot_id": lot.id,
                "sku": (tmpl.default_code or "")[:40],
                "active": tmpl.active,
                "qty": qty,
                "name": (tmpl.name or "")[:50],
            }
        )

print(f"Lots with internal qty > 0: {with_stock}")
print(f"Lots with zero internal stock: {without_stock}")

dupes = {sn: rows for sn, rows in by_serial.items() if len(rows) > 1}
dupes_in_stock = {
    sn: rows
    for sn, rows in dupes.items()
    if sum(1 for r in rows if r["qty"] > 0) > 1
    or (sum(1 for r in rows if r["qty"] > 0) >= 1 and len({r['sku'] for r in rows if r['qty']>0}) > 1)
}
print(f"\nSerial names appearing on >1 lot (any): {len(dupes)}")
print(f"Serial names on >1 product with stock: {len(dupes_in_stock)}")

print("\n--- Top duplicate SNs still in stock (first 20) ---")
shown = 0
for sn in sorted(dupes_in_stock):
    rows = [r for r in dupes_in_stock[sn] if r["qty"] > 0]
    if not rows:
        continue
    print(f"{sn} ({len(dupes_in_stock[sn])} lots total)")
    for r in dupes_in_stock[sn]:
        flag = "STOCK" if r["qty"] > 0 else "zero"
        act = "active" if r["active"] else "ARCHIVED"
        print(f"  [{flag}] {r['sku']} {act} qty={r['qty']}")
    shown += 1
    if shown >= 20:
        break

inactive_with_stock = []
for lot in lots:
    tmpl = lot.product_id.product_tmpl_id
    if tmpl.active:
        continue
    qty = sum(
        Quant.search(
            [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal"), ("quantity", ">", 0)]
        ).mapped("quantity")
    )
    if qty > 0:
        inactive_with_stock.append((lot.name, tmpl.default_code, qty))

print(f"\nArchived/inactive products still holding stock: {len(inactive_with_stock)}")
for row in inactive_with_stock[:15]:
    print(f"  {row[0]} | {row[1]} | qty={row[2]}")
