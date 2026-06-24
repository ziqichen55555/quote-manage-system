# -*- coding: utf-8 -*-
"""List every lot/quant for LAT3301 — real Blancco SN vs auto S/N-LAT3301-*."""
import re

SKU = "LAT3301"
AUTO_SN = re.compile(r"^S/N-LAT3301-\d{3}$", re.I)

Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()

tmpl = Template.search([("default_code", "=", SKU)], limit=1)
variants = Product.search(
    ["|", ("default_code", "=", SKU), ("product_tmpl_id", "=", tmpl.id)]
)

print(f"Template {tmpl.default_code!r} on_hand={tmpl.qty_available} tracking={tmpl.tracking}\n")

real_in_stock = []
auto_in_stock = []
other_in_stock = []
all_lots = Lot.browse()

for v in variants:
    print(f"--- variant id={v.id} code={v.default_code!r} active={v.active} qty={v.qty_available} ---")
    for lot in Lot.search([("product_id", "=", v.id)], order="name"):
        qs = Quant.search(
            [
                ("product_id", "=", v.id),
                ("lot_id", "=", lot.id),
                ("location_id.usage", "=", "internal"),
            ]
        )
        qty = sum(qs.mapped("quantity"))
        reserved = sum(qs.mapped("reserved_quantity"))
        if qty <= 0:
            tag = "empty"
        elif AUTO_SN.match(lot.name):
            tag = "AUTO"
            auto_in_stock.append((lot.name, qty, v.id))
        else:
            tag = "REAL?"
            real_in_stock.append((lot.name, qty, v.id))
        print(f"  [{tag}] {lot.name!r} qty={qty} reserved={reserved}")

no_lot = Quant.search(
    [
        ("product_id", "in", variants.ids),
        ("lot_id", "=", False),
        ("location_id.usage", "=", "internal"),
        ("quantity", ">", 0),
    ]
)
if no_lot:
    print(f"\nWARNING lot-less quants: {sum(no_lot.mapped('quantity'))}")

print("\n=== SUMMARY ===")
print(f"Real/custom SN in stock ({len(real_in_stock)}):")
for name, qty, vid in real_in_stock:
    print(f"  {name} qty={qty}")
print(f"Auto S/N-LAT3301-* in stock ({len(auto_in_stock)}):")
for name, qty, vid in auto_in_stock:
    print(f"  {name} qty={qty}")

SO = env["sale.order"].sudo()
print(f"\nSale orders (non-cancel): {SO.search([('state', '!=', 'cancel')]).mapped('name')}")
