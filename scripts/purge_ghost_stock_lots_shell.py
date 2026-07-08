# -*- coding: utf-8 -*-
"""Delete ghost stock.lot rows: zero internal qty (safe after fresh import).

Default DRY_RUN=True. Set False to unlink.

Production:
  Get-Content scripts/purge_ghost_stock_lots_shell.py -Raw |
    ssh ... docker compose run --rm -T web odoo shell ...
"""
from __future__ import annotations

DRY_RUN = True

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()

COMPANY = env.company


def internal_qty(lot) -> float:
    return float(
        sum(
            Quant.search(
                [
                    ("lot_id", "=", lot.id),
                    ("location_id.usage", "=", "internal"),
                    ("quantity", ">", 0),
                ]
            ).mapped("quantity")
        )
    )


def can_unlink(lot) -> bool:
    if internal_qty(lot) > 0:
        return False
    # Keep lots referenced on done customer deliveries (sold history).
    if MoveLine.search_count(
        [
            ("lot_id", "=", lot.id),
            ("state", "=", "done"),
            ("location_dest_id.usage", "=", "customer"),
        ],
        limit=1,
    ):
        return False
    return True


candidates = Lot.search([("company_id", "=", COMPANY.id)])
to_delete = env["stock.lot"]
skipped_stock = skipped_delivered = 0

for lot in candidates:
    if internal_qty(lot) > 0:
        skipped_stock += 1
        continue
    if not can_unlink(lot):
        skipped_delivered += 1
        continue
    to_delete |= lot

print(f"DRY_RUN={DRY_RUN}")
print(f"total lots: {len(candidates)}")
print(f"skip (has internal stock): {skipped_stock}")
print(f"skip (delivered history): {skipped_delivered}")
print(f"to delete (zero stock, no delivery lock): {len(to_delete)}")

inactive_deleted = active_deleted = 0
failed = 0
for lot in to_delete:
    tmpl_active = lot.product_id.product_tmpl_id.active
    if DRY_RUN:
        if tmpl_active:
            active_deleted += 1
        else:
            inactive_deleted += 1
        continue
    try:
        with env.cr.savepoint():
            zero_quants = Quant.search(
                [
                    ("lot_id", "=", lot.id),
                    ("quantity", "=", 0),
                ]
            )
            if zero_quants:
                zero_quants.unlink()
            lot.unlink()
        if tmpl_active:
            active_deleted += 1
        else:
            inactive_deleted += 1
    except Exception as exc:
        failed += 1
        if failed <= 5:
            print(f"FAIL unlink {lot.name} id={lot.id}: {exc}")

if not DRY_RUN:
    env.cr.commit()

print(f"deleted inactive-product lots: {inactive_deleted}")
print(f"deleted active-product zero-qty lots: {active_deleted}")
print(f"failed: {failed}")
remaining = Lot.search_count([("company_id", "=", COMPANY.id)])
print(f"remaining lots: {remaining}")
if DRY_RUN:
    print("Set DRY_RUN=False to apply.")
