# -*- coding: utf-8 -*-
"""Add MERGED 2026-09-11 48 devices onto existing CMOSP SKUs (additive, no upload)."""
import re

DRY_RUN = False

PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo().with_context(active_test=False)
Importer = env["product.csv.importer"].sudo()

WRONG_TO_RIGHT = {
    929: 828,
    930: 862,
    931: 831,
    932: 835,
    933: 863,
    934: 844,
    935: 846,
    936: 867,
    937: 870,
}

# MERGED import-ready 2026-09-11.csv (48 SUCCESS rows)
DEVICES = [
    ("PC1FVGPF", "20NYS4CP00-8G-512G-T-BT70-CMOSP", "103%"),
    ("PC2CN0L0", "20WNS6LL00-BT70-CMOSP", "97%"),
    ("PC1FVFC4", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC14S0AG", "20L8SDCE00-8G-256G-T-BTU70-CMOSP", "65%"),
    ("PC14S1HB", "20L8SDCE00-8G-256G-T-BTU70-CMOSP", "57%"),
    ("PC2CN0KP", "20WNS6LL00-BT70-CMOSP", "98%"),
    ("PC27R4C0", "20WN0025AU-BT70-CMOSP", "97%"),
    ("PC27R4BD", "20WN0025AU-BT70-CMOSP", "97%"),
    ("PC13Z0Z0", "20L8SBL100-BTU70-CMOSP", "91%"),
    ("PC2JNSG0", "20WNS6LL00-BT70-CMOSP", "97%"),
    ("PC27R1TA", "20WN0025AU-BT70-CMOSP", "99%"),
    ("PC2CMZKL", "20WNS6LL00-BT70-CMOSP", "81%"),
    ("PC2FFDFZ", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC27R3PG", "20WN0025AU-BT70-CMOSP", "98%"),
    ("PC1FVERQ", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC27R4BX", "20WN0025AU-BT70-CMOSP", "98%"),
    ("GM048TJE", "20WNA07YAU-BT70-CMOSP", "99%"),
    ("PC2CN0KW", "20WNS6LL00-BT70-CMOSP", "97%"),
    ("PC27R1WX", "20WN0025AU-BT70-CMOSP", "96%"),
    ("PC2JNSDR", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC23W0AA", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC2FFDH1", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC1FVNGB", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC2FFDGF", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC27R3PA", "20WN0025AU-BT70-CMOSP", "97%"),
    ("PC23W0C5", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC1TKK8M", "20T0003UAU-BT70-CMOSP", "103%"),
    ("PC23W0E9", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC23W0DX", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC23W0DS", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC2JNTRQ", "20WNS6LL00-BT70-CMOSP", "90%"),
    ("PC1FVND5", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC2JLEXC", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC1FVGP1", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC2JNTQS", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC2JNTQC", "20WNS6LL00-BT70-CMOSP", "99%"),
    ("PC13Z10H", "20L8SBL100-BTU70-CMOSP", "85%"),
    ("PC27R1VC", "20WN0025AU-BT70-CMOSP", "99%"),
    ("PC27R3ZC", "20WN0025AU-BT70-CMOSP", "72%"),
    ("PC1FVERH", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC1FVNJ5", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC23W09H", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC2CN0N5", "20WNS6LL00-BT70-CMOSP", "97%"),
    ("PC2CMZKK", "20WNS6LL00-BT70-CMOSP", "96%"),
    ("PC1FVESX", "20NYS4CP00-8G-256G-T-BT70-CMOSP", "103%"),
    ("PC23W08X", "20WNS1M500-BT70-CMOSP", "99%"),
    ("PC2CN0K7", "20WNS6LL00-BT70-CMOSP", "72%"),
    ("PC27R4BF", "20WN0025AU-BT70-CMOSP", "72%"),
]

wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
if not wh:
    raise RuntimeError("No warehouse")


def battery_percents(text):
    out = []
    for m in re.finditer(r"\d+", text or ""):
        n = int(m.group())
        if 0 < n <= 200:
            out.append(n)
    return out


def merge_battery_display(current, additions):
    nums = battery_percents(current)
    for item in additions:
        nums.extend(battery_percents(item))
    if not nums:
        return current or "Unknown"
    lo, hi = min(nums), max(nums)
    return f"{lo}%" if lo == hi else f"{lo}%-{hi}%"


def get_battery_attr(tmpl):
    attr = env.ref("quote_manage_ui.attr_battery", raise_if_not_found=False)
    if not attr:
        return ""
    line = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == attr)[:1]
    return " / ".join(line.value_ids.mapped("name")) if line else ""


def set_battery_attr(tmpl, display):
    if not display or DRY_RUN:
        return
    attr = env.ref("quote_manage_ui.attr_battery")
    Line = env["product.template.attribute.line"].sudo()
    Val = env["product.attribute.value"].sudo()
    val = Val.search(
        [("attribute_id", "=", attr.id), ("name", "=ilike", display)],
        limit=1,
    )
    if not val:
        val = Val.create({"attribute_id": attr.id, "name": display[:128]})
    line = Line.search(
        [("product_tmpl_id", "=", tmpl.id), ("attribute_id", "=", attr.id)],
        limit=1,
    )
    if line:
        line.write({"value_ids": [(6, 0, [val.id])]})
    else:
        Line.create(
            {
                "product_tmpl_id": tmpl.id,
                "attribute_id": attr.id,
                "value_ids": [(6, 0, [val.id])],
            }
        )


def add_serial_to_target(serial, target_sku):
    tmpl = PT.search([("default_code", "=", target_sku)], limit=1)
    if not tmpl:
        return "missing_sku"
    variant = tmpl.product_variant_ids[:1]
    if Importer._serial_was_sold(serial):
        return "sold_skip"

    existing = Quant.search_count([
        ("product_id", "=", variant.id),
        ("lot_id.name", "=", serial),
        ("location_id", "child_of", wh.lot_stock_id.id),
        ("quantity", ">", 0),
    ])
    if existing:
        return "already_on_target"

    wrong_lot = Lot.search([
        ("name", "=", serial),
        ("company_id", "=", env.company.id),
        ("product_id", "!=", variant.id),
    ], limit=1)
    if wrong_lot and not DRY_RUN:
        Importer._move_serial_lot_to_variant(wrong_lot, variant, wh)
        variant.invalidate_recordset()
        tmpl.invalidate_recordset()
        if Quant.search_count([
            ("product_id", "=", variant.id),
            ("lot_id.name", "=", serial),
            ("location_id", "child_of", wh.lot_stock_id.id),
            ("quantity", ">", 0),
        ]):
            return "moved"

    target_lot = Lot.search([
        ("product_id", "=", variant.id),
        ("name", "=", serial),
        ("company_id", "=", env.company.id),
    ], limit=1)
    if not target_lot and not DRY_RUN:
        target_lot = Lot.create({
            "product_id": variant.id,
            "name": serial,
            "company_id": env.company.id,
        })

    print(f"  {'[DRY] ' if DRY_RUN else ''}ADD {serial} -> {target_sku}")
    if DRY_RUN:
        return "would_add"

    dest = Quant.search([
        ("product_id", "=", variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
        ("lot_id", "=", target_lot.id),
    ], limit=1)
    if dest:
        dest.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 1.0})
    else:
        Quant.with_context(inventory_mode=True).create({
            "product_id": variant.id,
            "location_id": wh.lot_stock_id.id,
            "lot_id": target_lot.id,
            "inventory_quantity_auto_apply": 1.0,
        })
    return "added"


print("=" * 72)
print("ADD MERGED 48 TO OLD CMOSP SKUs")
print(f"DRY_RUN={DRY_RUN} devices={len(DEVICES)}")
print("=" * 72)

stats = {}
by_sku = {}
for serial, sku, bat in DEVICES:
    by_sku.setdefault(sku, []).append(bat)
    result = add_serial_to_target(serial, sku)
    stats[result] = stats.get(result, 0) + 1

print("\n--- Phase 2: refresh battery ranges ---")
for sku in sorted(by_sku):
    tmpl = PT.search([("default_code", "=", sku)], limit=1)
    if not tmpl:
        continue
    before = get_battery_attr(tmpl)
    after = merge_battery_display(before, by_sku[sku])
    print(f"  {sku}: battery {before!r} -> {after!r} on_hand={tmpl.qty_available:g}")
    set_battery_attr(tmpl, after)

print("\n--- Summary ---")
for k, v in sorted(stats.items()):
    print(f"  {k}: {v}")

expected = {
    "20L8SBL100-BTU70-CMOSP": 3,
    "20L8SDCE00-8G-256G-T-BTU70-CMOSP": 5,
    "20NYS4CP00-8G-256G-T-BT70-CMOSP": 28,
    "20NYS4CP00-8G-512G-T-BT70-CMOSP": 4,
    "20T0003UAU-BT70-CMOSP": 4,
    "20WN0025AU-BT70-CMOSP": 19,
    "20WNA07YAU-BT70-CMOSP": 2,
    "20WNS1M500-BT70-CMOSP": 14,
    "20WNS6LL00-BT70-CMOSP": 36,
}
print("\n--- Verification ---")
mismatch = 0
for sku, want in sorted(expected.items()):
    t = PT.search([("default_code", "=", sku)], limit=1)
    got = int(t.qty_available or 0) if t else -1
    ok = got == want
    if not ok:
        mismatch += 1
    print(f"  {'OK' if ok else 'MISMATCH'} {sku}: want={want} got={got}")

total = sum(int(PT.search([("default_code", "=", s)], limit=1).qty_available or 0) for s in expected)
print(f"\nTotal on 9 SKUs: {total} (baseline 120 + 48 = 168)")

if DRY_RUN:
    env.cr.rollback()
    print("\nPreview only.")
else:
    env.cr.commit()
    print("\nCommitted.")
