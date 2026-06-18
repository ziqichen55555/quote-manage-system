# -*- coding: utf-8 -*-
Template = env["product.template"].sudo()
Product = env["product.product"].sudo()
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()

templates = Template.search([("name", "ilike", "ThinkPad T14s")])
print("=== TEMPLATES matching ThinkPad T14s ===")
for t in templates:
    print(f"ID={t.id} code={t.default_code!r} name={t.name!r} track={t.tracking}")
    print(f"  qty_available={t.qty_available} virtual_available={t.virtual_available} free_qty={getattr(t,'free_qty',None)}")
    print(f"  variants={len(t.product_variant_ids)}")
    for v in t.product_variant_ids:
        lots = Lot.search([("product_id", "=", v.id)])
        quants = Quant.search([("product_id", "=", v.id), ("location_id.usage", "=", "internal")])
        lot_qty = sum(quants.mapped("quantity"))
        print(f"  variant id={v.id} code={v.default_code!r} display={v.display_name[:80]}")
        print(f"    lots={len(lots)} quant_qty={lot_qty} qty_available={v.qty_available}")
        if lots:
            print(f"    lot names sample: {lots[:5].mapped('name')}")

# Also search by series grouping if exists
print("\n=== ALL products with T14s in name ===")
prods = Product.search([("name", "ilike", "T14s")])
for p in prods:
    lots = Lot.search_count([("product_id", "=", p.id)])
    print(f"id={p.id} tmpl={p.product_tmpl_id.id} code={p.default_code!r} lots={lots} qty={p.qty_available} | {p.display_name[:90]}")
