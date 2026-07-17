# -*- coding: utf-8 -*-
"""Read-only: find Lots/Serials on 20T1S6C300 CMOSP/CMOSFL (incl. qty 0)."""
from __future__ import annotations

BASE = "20T1S6C300"

Lot = env["stock.lot"].sudo().with_context(active_test=False)
PT = env["product.template"].sudo().with_context(active_test=False)
PP = env["product.product"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()

print("=== 20T1S6C300 lot hunt (read-only) ===")

tmpls = PT.search([("default_code", "=ilike", BASE + "%")], order="default_code")
print(f"Templates matching {BASE}%: {len(tmpls)}")
for t in tmpls:
    print(
        f"  code={t.default_code!r} name={t.name!r} active={t.active} "
        f"published={t.website_published} qty={t.qty_available} tracking={t.tracking}"
    )

variants = PP.search([("default_code", "=ilike", BASE + "%")])
print(f"\nVariants: {len(variants)}")
for v in variants:
    print(f"  id={v.id} code={v.default_code!r} active={v.active} qty={v.qty_available}")

lots = Lot.search([("product_id", "in", variants.ids)], order="create_date desc, id desc")
print(f"\nLots on these variants (incl. inactive): {len(lots)}")

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
        "internal_qty": iq,
        "product_qty_field": float(lot.product_qty or 0),
    }
    (stocked if iq > 0 else ghost).append(row)

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
        f"lot_active={r['lot_active']} created={r['create_date']} lot_id={r['id']}"
    )

# Recent ghosts (likely manual Lots/Serial adds)
print("\n--- Zero-qty lots created >= 2026-07-14 ---")
recent = [r for r in ghost if r["create_date"] and r["create_date"] >= "2026-07-14"]
print(f"count={len(recent)}")
for r in recent:
    print(f"  SN={r['name']} sku={r['sku']} created={r['create_date']} lot_id={r['id']}")

# Also: any SKU containing T1S6C3 (typo variants)
print("\n--- Fuzzy template search T1S6 / 20T1S ---")
fuzzy = PT.search(["|", ("default_code", "ilike", "%T1S6%"), ("default_code", "ilike", "20T1S%")])
for t in fuzzy[:40]:
    print(f"  {t.default_code!r} qty={t.qty_available} active={t.active} name={t.name!r}")

print("\nDONE")
