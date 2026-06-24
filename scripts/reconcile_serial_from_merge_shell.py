# -*- coding: utf-8 -*-
"""
Reconcile all serial-tracked refurb products from MERGED import-ready CSV.

Prerequisites:
  1) Regenerate CSV with tools/reware_merge (run_merge.bat on Desktop folder)
     — use MERGED import-ready *-fixed.csv or today's date after script update
  2) Production on quote_manage_ui >= 1.0.119 (model-as-title for HP/Dell/Panasonic)
  3) DB backup before import

Merge CSV = source of truth for SN, qty, and Blancco-backed titles:
  Lenovo:     title = System version,  SKU = System model (MTM)
  HP/Dell/Panasonic: title = System model, SKU = System SKU number

Usage (local docker or prod via SSH pipe):
  Get-Content scripts/reconcile_serial_from_merge_shell.py |
    docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init

Or: Odoo backend → Inventory → Products → Upload inventory CSV (same reconcile logic).
"""
from pathlib import Path

DRY_RUN = True  # preview first; set False to apply
MERGE_CSV = r"/mnt/extra-addons/../../tools/reware_merge/MERGED import-ready 2026-06-24-fixed.csv"
# Windows Desktop (copy into repo tools/reware_merge/ or set path after scp to server):
# MERGE_CSV = "/mnt/custom-addons/quote_manage_ui/scripts/_prod_merge_import.csv"

Importer = env["product.csv.importer"].sudo()
path = Path(MERGE_CSV)
if not path.is_file():
    raise FileNotFoundError(f"Merge CSV not found: {path}")

text = path.read_text(encoding="utf-8-sig")
print(f"=== reconcile merge serial catalog ===")
print(f"file: {path.name}")
print(f"DRY_RUN: {DRY_RUN}")

result = Importer.reconcile_from_merge_csv_text(
    text, dry_run=DRY_RUN, refresh_products=not DRY_RUN
)

print(f"\ndevices in file: {result.get('devices_in_file')}")
print(f"FAILED rows skipped: {result.get('failed_devices')}")
print(f"SKUs reconciled: {result.get('reconcile_skus')}")
if not DRY_RUN:
    print(f"created: {result.get('created')} updated: {result.get('updated')}")
    print(f"serials zeroed (wrong/extra): {result.get('serials_zeroed')}")
print(f"orphan refurb SKUs (serial stock, not in CSV): {result.get('orphan_skus')}")

needs = [r for r in result.get("sku_reconcile") or [] if r.get("needs_sync")]
if DRY_RUN and needs:
    print(f"\n--- SKUs needing sync ({len(needs)}) ---")
    for r in needs[:30]:
        print(
            f"  {r['sku']}: on_hand={r['on_hand']} expected={r['expected_qty']} "
            f"extra={r.get('extra_serials')} missing={r.get('missing_serials')} "
            f"no_lot={r.get('no_lot_qty')}"
        )
    if len(needs) > 30:
        print(f"  ... and {len(needs) - 30} more")

orphans = result.get("orphan_serial_products") or []
if orphans:
    print(f"\n--- Orphans (review manually) ---")
    for o in orphans[:20]:
        print(f"  {o['sku']}: on_hand={o['on_hand']} lots={o.get('lots_in_stock')}")

if DRY_RUN:
    print("\nSet DRY_RUN = False and re-run to apply.")
else:
    print("\nDone. Re-check website stock + delivery SN dropdown.")
