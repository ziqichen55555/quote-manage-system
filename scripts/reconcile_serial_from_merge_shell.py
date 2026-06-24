# -*- coding: utf-8 -*-
"""
Reconcile all serial-tracked refurb products from MERGED import-ready CSV.

Merge CSV = source of truth for:
  - which serial numbers exist per SKU
  - how many units (len(serials))
  - product name + Blancco CPU/RAM/SSD/Series attrs

Steps when DRY_RUN=False:
  1) Additive merge import (refresh product info, create missing SKUs)
  2) sync_serial_stock_allowlist per SKU (zero wrong/auto SNs, fix qty)

Monitors / bags / services are NOT in merge CSV → untouched.

Usage (local docker, repo root):
  Get-Content scripts/reconcile_serial_from_merge_shell.py |
    docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init

Set MERGE_CSV to your file path inside the container or mount path.
"""
from pathlib import Path

DRY_RUN = True  # preview first; set False to apply
MERGE_CSV = r"/mnt/extra-addons/../../tools/reware_merge/MERGED import-ready 2026-06-19.csv"
# Or on prod copy after scp:
# MERGE_CSV = "/tmp/MERGED-import-ready.csv"

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
