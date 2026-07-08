# -*- coding: utf-8 -*-
"""Production fresh catalog: merge old listings + import MERGED import-all CSV."""
from pathlib import Path

DRY_RUN = False
MERGE_CSV = "/mnt/custom-addons/quote_manage_ui/scripts/MERGED-import-all-2026-07-08.csv"

Importer = env["product.csv.importer"].sudo()
path = Path(MERGE_CSV)
if not path.is_file():
    raise FileNotFoundError(f"Missing {MERGE_CSV}")

print("=== 1) Merge existing products (Configuration dropdown) ===")
if DRY_RUN:
    print("skip (DRY_RUN)")
else:
    merge_res = Importer.merge_existing_catalog()
    print(merge_res)

print("\n=== 2) Consolidate RW-* legacy SKUs ===")
if DRY_RUN:
    print("skip (DRY_RUN)")
elif hasattr(Importer, "consolidate_legacy_rw_skus"):
    print(Importer.consolidate_legacy_rw_skus())
else:
    print("method not available")

print("\n=== 3) Import MERGED import-all ===")
text = path.read_text(encoding="utf-8-sig")
result = Importer.reconcile_from_merge_csv_text(
    text, dry_run=DRY_RUN, refresh_products=not DRY_RUN
)
print(Importer.format_import_result_message(result) if hasattr(Importer, "format_import_result_message") else result)

if not DRY_RUN:
    env.cr.commit()
    print("\nCommitted.")
