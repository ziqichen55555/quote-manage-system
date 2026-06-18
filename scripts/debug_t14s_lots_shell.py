# -*- coding: utf-8 -*-
Lot = env["stock.lot"].sudo()
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()

# All lots linked to any T14s variant
variants = Product.search([("product_tmpl_id.name", "ilike", "ThinkPad T14s")])
lots = Lot.search([("product_id", "in", variants.ids)])
print("VARIANT_COUNT:", len(variants))
print("TOTAL_LOTS_ALL_VARIANTS:", len(lots))
print("SUM_QTY:", sum(variants.mapped("qty_available")))

# Lots without product or duplicate?
for v in variants:
    lc = Lot.search_count([("product_id", "=", v.id)])
    print(f"  {v.default_code}: lots={lc} qty={v.qty_available}")

# Any other T14s templates?
tmpls = Template.search([("name", "ilike", "T14s")])
print("\nALL T14s TEMPLATES:")
for t in tmpls:
    print(f"  tmpl={t.id} name={t.name!r} variants={len(t.product_variant_ids)} qty={t.qty_available}")

# Quants without lot on serial products
Quant = env["stock.quant"].sudo()
for v in variants:
    quants = Quant.search([("product_id", "=", v.id), ("location_id.usage", "=", "internal"), ("quantity", ">", 0)])
    no_lot = quants.filtered(lambda q: not q.lot_id)
    if no_lot:
        print(f"NO LOT QUANTS {v.default_code}: {no_lot.mapped('quantity')}")

# Website qty method
t = Template.browse(757)
print("\n_rw_website_available_qty:", t._rw_website_available_qty())
