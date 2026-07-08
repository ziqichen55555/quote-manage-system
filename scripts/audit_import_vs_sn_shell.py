# -*- coding: utf-8 -*-
"""Explain import-all row count vs Odoo serial products."""
from collections import defaultdict

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()

cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
cat_d = env.ref("quote_manage_ui.public_cat_desktops").id

# Serial refurb templates (laptops + desktops)
refurb = PT.search(
    [
        ("type", "=", "product"),
        ("tracking", "=", "serial"),
        ("public_categ_ids", "in", [cat_l, cat_d]),
    ]
)
active_refurb = refurb.filtered(lambda t: t.active)
published = refurb.filtered(lambda t: t.website_published)

with_stock = []
for t in active_refurb:
    oh = float(t.qty_available or 0)
    if oh > 0:
        with_stock.append(t)

lots_in_stock = Lot.search([])
lots_with_qty = 0
for lot in lots_in_stock:
    q = sum(
        Quant.search(
            [("lot_id", "=", lot.id), ("location_id.usage", "=", "internal"), ("quantity", ">", 0)]
        ).mapped("quantity")
    )
    if q > 0:
        lots_with_qty += 1

cmosp = active_refurb.filtered(lambda t: (t.default_code or "").upper().endswith("-CMOSP"))
cmosfl = active_refurb.filtered(lambda t: (t.default_code or "").upper().endswith("-CMOSFL"))

print("=== Odoo refurb serial products ===")
print(f"all refurb serial templates (incl inactive): {len(refurb)}")
print(f"active refurb serial templates: {len(active_refurb)}")
print(f"website_published: {len(published)}")
print(f"active with qty_available > 0: {len(with_stock)}")
print(f"stock.lot with internal qty > 0: {lots_with_qty}")
print(f"active -CMOSP SKUs: {len(cmosp)}")
print(f"active -CMOSFL SKUs (warehouse): {len(cmosfl)}")

cmosp_stock = sum(float(t.qty_available or 0) for t in cmosp)
cmosfl_stock = sum(float(t.qty_available or 0) for t in cmosfl)
print(f"CMOSP units on hand: {int(cmosp_stock)}")
print(f"CMOSFL units on hand: {int(cmosfl_stock)}")

# By category
for label, cat_id in [("Laptops", cat_l), ("Desktops", cat_d)]:
    ts = active_refurb.filtered(lambda t, c=cat_id: c in t.public_categ_ids.ids)
    stocked = [t for t in ts if float(t.qty_available or 0) > 0]
    print(f"\n{label}: {len(ts)} active SKUs, {len(stocked)} with stock, units={int(sum(t.qty_available for t in stocked))}")

# Sample top SKUs by serial count
print("\n--- Top SKUs by on_hand (serials) ---")
ranked = sorted(with_stock, key=lambda t: -float(t.qty_available or 0))[:15]
for t in ranked:
    print(f"  {t.default_code}: on_hand={int(t.qty_available)} published={t.website_published}")
