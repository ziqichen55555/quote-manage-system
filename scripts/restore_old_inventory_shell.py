# -*- coding: utf-8 -*-
"""Restore real old inventory: re-enable old SKUs + serial qty on old variants; remove mistaken 929-937."""
from datetime import datetime

DRY_RUN = True
confirm_apply = ""  # GH workflow: confirm_apply=APPLY when DRY_RUN=False

PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo().with_context(active_test=False)

IMPORT_DAY = datetime(2026, 9, 11)
ARCHIVE_START = IMPORT_DAY.replace(hour=4, minute=58, second=0)
ARCHIVE_END = IMPORT_DAY.replace(hour=4, minute=59, second=0)
MISTAKE_NEW_IDS = list(range(929, 938))
# 31 old SKUs archived at mistaken merge (from prod investigation)
KNOWN_OLD_IDS = [
    902, 886, 823, 874, 873, 827, 872, 822, 840, 839, 863, 844, 846, 866,
    871, 867, 868, 870, 842, 864, 865, 857, 862, 859, 828, 860, 831, 836,
    833, 835, 848,
]

wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
if not wh:
    raise RuntimeError("No warehouse")


def stock_quants(variant):
    return Quant.search([
        ("product_id", "=", variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
    ])


def lot_should_restore(name):
    n = (name or "").strip().upper()
    if not n:
        return False
    if "_INVALID" in n or n.endswith("-OLD") or n.endswith("_OLD"):
        return False
    return True


def restore_serial_on_old_variant(tmpl):
    """Re-apply on-hand for serial lots still owned by this old SKU (qty was zeroed by import move)."""
    variant = tmpl.product_variant_ids[:1]
    if not variant or tmpl.tracking != "serial":
        return 0, 0
    lots = Lot.search([("product_id", "=", variant.id)], order="name")
    restored = skipped = 0
    for lot in lots:
        if not lot_should_restore(lot.name):
            continue
        q = Quant.search([
            ("product_id", "=", variant.id),
            ("location_id", "child_of", wh.lot_stock_id.id),
            ("lot_id", "=", lot.id),
        ], limit=1)
        if q and float(q.quantity or 0) >= 1:
            skipped += 1
            continue
        print(f"    SN {lot.name} -> {tmpl.default_code}")
        if not DRY_RUN:
            if q:
                q.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 1.0})
            else:
                Quant.with_context(inventory_mode=True).create({
                    "product_id": variant.id,
                    "location_id": wh.lot_stock_id.id,
                    "lot_id": lot.id,
                    "inventory_quantity_auto_apply": 1.0,
                })
        restored += 1
    return restored, skipped


def remove_mistake_product(tmpl):
    variant = tmpl.product_variant_ids[:1]
    if not variant:
        return "no_variant"
    for q in stock_quants(variant):
        if float(q.quantity or 0) == 0:
            continue
        label = q.lot_id.name if q.lot_id else "(no lot)"
        print(f"    zero {label} qty={q.quantity}")
        if not DRY_RUN:
            q.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 0.0})
    if not DRY_RUN:
        tmpl.write({"active": False, "sale_ok": False})
        tmpl.product_variant_ids.write({"active": False})
    return "archived"


# Real old catalog (explicit IDs — write_date window misses re-activated templates)
old_skus = PT.browse(KNOWN_OLD_IDS).exists().sorted(key=lambda t: t.default_code or "")

print("=" * 72)
print("RESTORE OLD INVENTORY (old SKU + SN on old product)")
print(f"DRY_RUN={DRY_RUN}")
print("=" * 72)

print(f"\nOld SKU batch (merge archive window): {len(old_skus)}")

stats = {"flags": 0, "sn_restored": 0, "sn_skip": 0, "mistake_removed": 0}

print("\n--- Phase 1: old products active + sale_ok + SN stock on OLD variant ---")
for tmpl in old_skus.sorted(key=lambda t: t.default_code or ""):
    ref = tmpl.default_code or f"ID{tmpl.id}"
    before = float(tmpl.qty_available or 0)
    print(f"\n{ref} (ID={tmpl.id}) active={tmpl.active} on_hand={before:g}")
    if not DRY_RUN:
        tmpl.write({
            "active": True,
            "sale_ok": True,
            "website_published": True,
        })
        tmpl.product_variant_ids.write({"active": True})
    else:
        print(f"  [DRY] active=True sale_ok=True website_published=True")
    stats["flags"] += 1
    n, sk = restore_serial_on_old_variant(tmpl)
    stats["sn_restored"] += n
    stats["sn_skip"] += sk
    after = before if DRY_RUN else float(tmpl.qty_available or 0)
    if not DRY_RUN:
        print(f"  on_hand now={after:g} (restored {n} SN, already ok {sk})")
    else:
        print(f"  would restore {n} SN, already ok {sk}")

if not DRY_RUN:
    env.cr.commit()
    print("\nPhase 1 committed.")

print("\n--- Phase 2: archive mistaken import products 929-937 (keep lots, no unlink) ---")
for mid in MISTAKE_NEW_IDS:
    tmpl = PT.browse(mid)
    if not tmpl.exists():
        print(f"ID {mid}: missing")
        continue
    print(f"\nID={mid} {tmpl.default_code}")
    result = remove_mistake_product(tmpl)
    print(f"  -> {result}")
    stats["mistake_removed"] += 1

print("\n" + "=" * 72)
print(f"Old SKUs processed: {stats['flags']}")
print(f"SN restored / would restore: {stats['sn_restored']}")
print(f"SN already on hand: {stats['sn_skip']}")
print(f"Mistake products handled: {stats['mistake_removed']}")

if DRY_RUN:
    print("\nPreview only. Set DRY_RUN=False + confirm_apply=APPLY to apply.")
    env.cr.rollback()
else:
    env.cr.commit()
    print("\nCommitted.")
