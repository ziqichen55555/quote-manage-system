# -*- coding: utf-8 -*-
"""Read-only: find Lots/Serials on T14s 20WN0025AU CMOSP/CMOSFL (incl. qty 0)."""
from __future__ import annotations

FAIL_SKU = "20WN0025AU-BT70-CMOSFL"
PASS_SKU = "20WN0025AU-BT70-CMOSP"
KNOWN = "PC27R1V2"

Lot = env["stock.lot"].sudo().with_context(active_test=False)
PT = env["product.template"].sudo().with_context(active_test=False)
PP = env["product.product"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()

print("=== T14s CMOS lot hunt (read-only) ===")

for code in (FAIL_SKU, PASS_SKU):
    tmpls = PT.search([("default_code", "=", code)])
    print(f"\nSKU {code}: templates={len(tmpls)}")
    for t in tmpls:
        print(
            f"  tmpl_id={t.id} active={t.active} published={t.website_published} "
            f"qty_available={t.qty_available} tracking={t.tracking}"
        )
        for v in t.product_variant_ids:
            print(
                f"    variant_id={v.id} code={v.default_code!r} "
                f"active={v.active} qty={v.qty_available}"
            )

variants = PP.search(
    [
        "|",
        ("default_code", "=", FAIL_SKU),
        ("default_code", "=", PASS_SKU),
    ]
)
print(f"\nVariants matched: {len(variants)} ids={variants.ids}")

lots = Lot.search([("product_id", "in", variants.ids)], order="create_date desc, id desc")
print(f"Lots on these variants (incl. inactive): {len(lots)}")

ghost = []
stocked = []
for lot in lots:
    iq = float(
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
    row = {
        "id": lot.id,
        "name": lot.name,
        "sku": lot.product_id.default_code,
        "product_active": lot.product_id.active,
        "lot_active": getattr(lot, "active", True),
        "create_date": str(lot.create_date),
        "write_date": str(lot.write_date),
        "internal_qty": iq,
        "product_qty_field": float(lot.product_qty or 0),
    }
    if iq > 0:
        stocked.append(row)
    else:
        ghost.append(row)

print(f"\n--- Stocked lots ({len(stocked)}) ---")
for r in stocked:
    print(
        f"  {r['name']:16} sku={r['sku']} qty={r['internal_qty']} "
        f"created={r['create_date']} lot_id={r['id']}"
    )

print(f"\n--- Ghost / zero-qty lots ({len(ghost)}) ---")
for r in ghost:
    print(
        f"  {r['name']:16} sku={r['sku']} qty={r['internal_qty']} "
        f"lot_active={r['lot_active']} product_active={r['product_active']} "
        f"created={r['create_date']} lot_id={r['id']}"
    )

# Also: any lot named like known SN anywhere
print(f"\n--- All lots named {KNOWN!r} (any product) ---")
for lot in Lot.search([("name", "=ilike", KNOWN)]):
    print(
        f"  lot_id={lot.id} name={lot.name} sku={lot.product_id.default_code!r} "
        f"product_qty={lot.product_qty} created={lot.create_date}"
    )

# Recent zero-qty lots created mid-July on PASS sku (likely the 5 they added)
print("\n--- Recent CMOSP zero-qty lots (create_date >= 2026-07-14) ---")
recent_ghost = [
    r
    for r in ghost
    if r["sku"] == PASS_SKU and r["create_date"] and r["create_date"] >= "2026-07-14"
]
print(f"count={len(recent_ghost)}")
for r in recent_ghost:
    print(f"  SN={r['name']} created={r['create_date']} lot_id={r['id']}")

print("\nDONE")
