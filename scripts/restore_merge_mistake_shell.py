# -*- coding: utf-8 -*-
"""Undo mistaken merge upload: reactivate 31 archived SKUs, remove 9 mistaken new products."""
from datetime import datetime, timedelta

DRY_RUN = True
confirm_apply = ""  # set confirm_apply=APPLY in GH workflow when DRY_RUN=False

PT = env["product.template"].sudo().with_context(active_test=False)
PP = env["product.product"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SOL = env["sale.order.line"].sudo()
SML = env["stock.move.line"].sudo()
SM = env["stock.move"].sudo()

# Import batches from prod investigation (UTC server time, 2026-09-11)
IMPORT_DAY = datetime(2026, 9, 11)
NEW_START = IMPORT_DAY.replace(hour=4, minute=57, second=0)
NEW_END = IMPORT_DAY.replace(hour=4, minute=58, second=0)
ARCHIVE_START = IMPORT_DAY.replace(hour=4, minute=58, second=0)
ARCHIVE_END = IMPORT_DAY.replace(hour=4, minute=59, second=0)

KNOWN_NEW_IDS = list(range(929, 938))  # 9 products created by mistaken import


def unlink_blockers(tmpl):
    variants = tmpl.product_variant_ids
    v_ids = variants.ids
    blockers = []
    oh = float(tmpl.qty_available or 0)
    if oh != 0:
        blockers.append(f"on_hand={oh}")
    for label, model, domain in (
        ("sale_order_lines", SOL, [("product_id", "in", v_ids)]),
        ("stock_move_lines", SML, [("product_id", "in", v_ids)]),
        ("stock_moves", SM, [("product_id", "in", v_ids)]),
    ):
        n = model.search_count(domain)
        if n:
            blockers.append(f"{label}={n}")
    n = Quant.search_count([("product_id", "in", v_ids), ("quantity", "!=", 0)])
    if n:
        blockers.append(f"nonzero_quants={n}")
    return blockers


def zero_product_stock(tmpl):
    """Zero on-hand before delete so mistaken import stock does not block unlink."""
    variant = tmpl.product_variant_ids[:1]
    if not variant:
        return 0
    wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
    if not wh:
        return 0
    quants = Quant.search([
        ("product_id", "=", variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
        ("quantity", "!=", 0),
    ])
    zeroed = 0
    for q in quants:
        label = q.lot_id.name if q.lot_id else "(no lot)"
        print(f"    zero quant id={q.id} lot={label} qty={q.quantity}")
        if not DRY_RUN:
            q.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 0.0})
        zeroed += 1
    return zeroed


print("=" * 72)
print("RESTORE MERGE MISTAKE")
print(f"DRY_RUN={DRY_RUN}")
print("=" * 72)

# --- 1) Mistaken new products ---
new_products = PT.browse(KNOWN_NEW_IDS).exists()
new_by_time = PT.search([
    ("create_date", ">=", NEW_START),
    ("create_date", "<", NEW_END),
])
print(f"\nNew products (known IDs {KNOWN_NEW_IDS}): {len(new_products)}")
print(f"New products (create window 04:57): {len(new_by_time)}")
for p in new_products:
    print(f"  DELETE candidate ID={p.id} ref={p.default_code} on_hand={p.qty_available}")

# --- 2) Archived batch to restore ---
archived_batch = PT.search([
    ("active", "=", False),
    ("write_date", ">=", ARCHIVE_START),
    ("write_date", "<", ARCHIVE_END),
])
print(f"\nArchived batch to restore (write window 04:58): {len(archived_batch)}")
for p in archived_batch[:15]:
    print(f"  RESTORE ID={p.id} ref={p.default_code} name={p.name}")
if len(archived_batch) > 15:
    print(f"  ... and {len(archived_batch) - 15} more")

restored = []
deleted = []
skipped_delete = []

print("\n--- Phase A: restore archived ---")
for tmpl in archived_batch:
    label = f"ID={tmpl.id} ref={tmpl.default_code}"
    print(f"{'[DRY] RESTORE' if DRY_RUN else 'RESTORE'} {label}")
    if not DRY_RUN:
        tmpl.write({"active": True})
        tmpl.product_variant_ids.write({"active": True})
    restored.append(label)

print("\n--- Phase B: remove mistaken new products ---")
for tmpl in new_products:
    label = f"ID={tmpl.id} ref={tmpl.default_code}"
    blockers = unlink_blockers(tmpl)
    if blockers and any("on_hand" in b or "nonzero_quants" in b for b in blockers):
        print(f"  {label}: clearing stock first ({', '.join(blockers)})")
        zero_product_stock(tmpl)
        blockers = unlink_blockers(tmpl)
    if blockers:
        skipped_delete.append((label, blockers))
        print(f"SKIP DELETE {label}: {', '.join(blockers)}")
        continue
    print(f"{'[DRY] DELETE' if DRY_RUN else 'DELETE'} {label}")
    if not DRY_RUN:
        tmpl.unlink()
    deleted.append(label)

print("\n" + "=" * 72)
print(f"Would restore / restored: {len(restored)}")
print(f"Would delete / deleted: {len(deleted)}")
print(f"Skipped delete: {len(skipped_delete)}")
if skipped_delete:
    for label, blockers in skipped_delete:
        print(f"  {label}: {', '.join(blockers)}")

if DRY_RUN:
    print("\nPreview only. Set DRY_RUN=False + confirm_apply=APPLY to apply.")
    env.cr.rollback()
else:
    env.cr.commit()
    print("\nCommitted.")
