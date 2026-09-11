# -*- coding: utf-8 -*-
"""Move serial lots from archived mistaken import products (929-937) back to restored SKUs."""
DRY_RUN = True
confirm_apply = ""  # set confirm_apply=APPLY in GH workflow when DRY_RUN=False

PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo().with_context(active_test=False)

WRONG_TO_RIGHT = {
    929: 828,   # 20L8SBL100 -> 20L8SBL100-BTU70-CMOSP (only restored L8SBL100)
    930: 862,   # 20L8SDCE00-8G-256G-N-BTU70-CMOSP
    931: 831,   # 20NYS4CP00-8G-256G-N-BT70-CMOSP
    932: 835,   # 20NYS4CP00-8G-512G-N-BT70-CMOSP
    933: 863,   # 20T0003UAU-16G-256G-N-BT70-CMOSP
    934: 844,   # 20WN0025AU-16G-256G-N-BT70-CMOSP
    935: 846,   # 20WNA07YAU-16G-256G-N-BT70-CMOSP
    936: 867,   # 20WNS1M500-8G-256G-N-BT70-CMOSP
    937: 870,   # 20WNS6LL00-16G-256G-N-BT70-CMOSP
}


def apply_lot_on_target(lot_name, target_variant, wh):
    """Ensure one serial unit exists on target_variant (source may already be zeroed)."""
    target_lot = Lot.search(
        [
            ("product_id", "=", target_variant.id),
            ("name", "=", lot_name),
            ("company_id", "=", env.company.id),
        ],
        limit=1,
    )
    if not target_lot:
        if DRY_RUN:
            print(f"    [DRY] would create lot {lot_name} on {target_variant.default_code}")
        else:
            target_lot = Lot.create(
                {
                    "product_id": target_variant.id,
                    "name": lot_name,
                    "company_id": env.company.id,
                }
            )

    dest = Quant.search(
        [
            ("product_id", "=", target_variant.id),
            ("location_id", "child_of", wh.lot_stock_id.id),
            ("lot_id.name", "=", lot_name),
        ],
        limit=1,
    )
    if dest and float(dest.quantity or 0) >= 1:
        return "skip_exists"

    label = target_variant.default_code or target_variant.display_name
    print(f"    {'[DRY] RESTORE' if DRY_RUN else 'RESTORE'} SN {lot_name} -> {label}")
    if DRY_RUN:
        return "would_restore"

    if dest:
        dest.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 1.0})
    else:
        lot_rec = target_lot or Lot.search(
            [
                ("product_id", "=", target_variant.id),
                ("name", "=", lot_name),
            ],
            limit=1,
        )
        Quant.with_context(inventory_mode=True).create(
            {
                "product_id": target_variant.id,
                "location_id": wh.lot_stock_id.id,
                "lot_id": lot_rec.id,
                "inventory_quantity_auto_apply": 1.0,
            }
        )
    return "restored"


wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
if not wh:
    raise RuntimeError("No warehouse found")

print("=" * 72)
print("RESTORE MERGE SN STOCK")
print(f"DRY_RUN={DRY_RUN}")
print("=" * 72)

stats = {"restored": 0, "skip_exists": 0, "would_restore": 0, "pairs": 0}

for wrong_id, right_id in WRONG_TO_RIGHT.items():
    wrong = PT.browse(wrong_id)
    right = PT.browse(right_id)
    if not wrong.exists() or not right.exists():
        print(f"\nSKIP pair {wrong_id}->{right_id}: missing template")
        continue
    if not right.active:
        print(f"\nWARN {right_id} {right.default_code} is not active")

    wvar = wrong.product_variant_ids[:1]
    rvar = right.product_variant_ids[:1]
    lots = Lot.search([("product_id", "=", wvar.id)], order="name")
    print(
        f"\n{wrong_id} {wrong.default_code} -> {right_id} {right.default_code} "
        f"({len(lots)} lots on wrong product, target on_hand={right.qty_available:g})"
    )
    stats["pairs"] += 1
    for lot in lots:
        result = apply_lot_on_target(lot.name, rvar, wh)
        stats[result] = stats.get(result, 0) + 1

print("\n" + "=" * 72)
print(f"Pairs processed: {stats['pairs']}")
print(f"Restored / would restore: {stats.get('restored', 0) + stats.get('would_restore', 0)}")
print(f"Already on target: {stats.get('skip_exists', 0)}")

if DRY_RUN:
    print("\nPreview only. Set DRY_RUN=False + confirm_apply=APPLY to apply.")
    env.cr.rollback()
else:
    env.cr.commit()
    print("\nCommitted.")
