# -*- coding: utf-8 -*-
"""Apply pack dimensions from CSV (same product_id column as product_weights_prod.csv).

CSV columns (header required):
  product_id,length_cm,width_cm,height_cm
Optional: default_code (for validation only)

Master file: exports/product_weights_prod.csv (weight + L/W/H). Upload to
/tmp/product_weights_prod.csv on server.

DRY_RUN=True by default.
"""
DRY_RUN = True
CSV_PATH = "/tmp/product_weights_prod.csv"

import csv

Template = env["product.template"].sudo()

print("=" * 72)
print(f"apply_product_pack_dims_csv DRY_RUN={DRY_RUN} path={CSV_PATH!r}")
try:
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
except FileNotFoundError:
    print(f"ERROR: file not found: {CSV_PATH}")
    print("Upload CSV to server or set CSV_PATH in script.")
    rows = []

updated = 0
for row in rows:
    try:
        pid = int(row["product_id"])
    except (KeyError, ValueError, TypeError):
        print(f"SKIP bad row: {row}")
        continue
    try:
        l_cm = float(row["length_cm"])
        w_cm = float(row["width_cm"])
        h_cm = float(row["height_cm"])
    except (KeyError, ValueError, TypeError):
        print(f"SKIP missing dims: id={pid}")
        continue
    if min(l_cm, w_cm, h_cm) <= 0:
        print(f"SKIP non-positive dims: id={pid}")
        continue
    t = Template.browse(pid)
    if not t.exists():
        print(f"MISSING template id={pid}")
        continue
    code = (row.get("default_code") or "").strip()
    if code and (t.default_code or "").strip() != code:
        print(f"WARN id={pid} code mismatch csv={code!r} db={t.default_code!r}")
    old = (t.rw_ship_length_cm, t.rw_ship_width_cm, t.rw_ship_height_cm)
    new = (l_cm, w_cm, h_cm)
    if old != new:
        print(f"  id={pid} {old} -> {new} | {t.name[:45]}")
        if not DRY_RUN:
            t.write(
                {
                    "rw_ship_length_cm": l_cm,
                    "rw_ship_width_cm": w_cm,
                    "rw_ship_height_cm": h_cm,
                }
            )
        updated += 1

if DRY_RUN:
    print(f"Would update {updated} templates.")
else:
    env.cr.commit()
    print(f"APPLIED {updated} templates.")
print("Done.")
