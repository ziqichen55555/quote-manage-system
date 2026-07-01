# -*- coding: utf-8 -*-
"""Check which MERGED import-not-ready serials are already delivered (sold).

Pipe JSON array on stdin, e.g. from local helper:
  [{"serial":"PC1ACZKV","shop_sku":"...","mtm":"...","reason":"..."}, ...]

Production:
  Get-Content serials.json -Raw | ssh ... odoo shell ... < scripts/check_not_ready_delivered_shell.py
"""
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    print("No stdin JSON")
    raise SystemExit(1)

rows = json.loads(raw)
Importer = env["product.csv.importer"].sudo()
Lot = env["stock.lot"].sudo()
MoveLine = env["stock.move.line"].sudo()
company = env.company

delivered = []
not_delivered = []
no_lot = []

for row in rows:
    serial = (row.get("serial") or "").strip()
    if not serial:
        continue
    lots = Lot.search(
        [
            ("name", "=ilike", serial),
            ("company_id", "=", company.id),
        ]
    )
    is_delivered = False
    delivery_info = None
    if lots:
        ml = MoveLine.search(
            [
                ("lot_id", "in", lots.ids),
                ("state", "=", "done"),
                ("location_dest_id.usage", "=", "customer"),
            ],
            order="date desc",
            limit=1,
        )
        if ml:
            is_delivered = True
            so = ml.move_id.sale_line_id.order_id if ml.move_id.sale_line_id else False
            delivery_info = {
                "picking": ml.picking_id.name if ml.picking_id else "",
                "date": str(ml.date) if ml.date else "",
                "order": so.name if so else "",
                "product_code": (ml.product_id.default_code or "").strip(),
                "product_name": ml.product_id.display_name,
            }
    else:
        # fallback: importer helper without product_id
        if Importer._serial_is_delivered(serial):
            is_delivered = True
            delivery_info = {"product_code": "", "product_name": "(lot found via importer)"}

    entry = {**row, **(delivery_info or {})}
    if is_delivered:
        delivered.append(entry)
    elif not lots and not Importer._serial_is_delivered(serial):
        no_lot.append(entry)
    else:
        not_delivered.append(entry)

print("=" * 72)
print("MERGED import-not-ready — delivered (sold) check")
print("=" * 72)
print(f"Total checked: {len(rows)}")
print(f"Already delivered (sold): {len(delivered)}")
print(f"In Odoo, not delivered: {len(not_delivered)}")
print(f"No lot in Odoo: {len(no_lot)}")
print()

if delivered:
    print("--- DELIVERED (SOLD) ---")
    for d in sorted(delivered, key=lambda x: (x.get("reason", ""), x.get("serial", ""))):
        print(
            f"{d.get('serial'):<12}  {d.get('shop_sku',''):<40}  "
            f"reason={d.get('reason','')}  order={d.get('order','')}  "
            f"picking={d.get('picking','')}  sku={d.get('product_code','')}"
        )
else:
    print("No delivered serials in this not-ready file.")

print()
print("Done.")
