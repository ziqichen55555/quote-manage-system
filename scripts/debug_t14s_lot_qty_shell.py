# -*- coding: utf-8 -*-
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
Product = env["product.product"].sudo()

variants = Product.search([("product_tmpl_id.name", "=", "ThinkPad T14s")])
lots = Lot.search([("product_id", "in", variants.ids)])
print("ALL_LOTS:", len(lots))

# Lots with on-hand qty > 0
on_hand_lots = set()
for v in variants:
    quants = Quant.search([
        ("product_id", "=", v.id),
        ("location_id.usage", "=", "internal"),
        ("quantity", ">", 0),
        ("lot_id", "!=", False),
    ])
    for q in quants:
        on_hand_lots.add(q.lot_id.id)
print("LOTS_WITH_ON_HAND_QTY:", len(on_hand_lots))

# Lots with zero qty (sold/reserved moved out)
zero_lot_ids = [l.id for l in lots if l.id not in on_hand_lots]
print("LOTS_ZERO_OR_NO_INTERNAL:", len(zero_lot_ids))
