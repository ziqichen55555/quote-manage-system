# -*- coding: utf-8 -*-
"""Cancel all SOs + trim LAT3301 to 7 serial units."""
Importer = env["product.csv.importer"].sudo()
SKU = "LAT3301"
TARGET = 7

SO = env["sale.order"].sudo()
cancelled = []
for order in SO.search([], order="name"):
    if order.state == "cancel":
        continue
    for p in order.picking_ids.filtered(lambda x: x.state not in ("done", "cancel")):
        p.action_cancel()
    if order.state in ("draft", "sent", "sale"):
        order.action_cancel()
    cancelled.append(order.name)

trim = Importer.trim_serial_stock_to_count(SKU, TARGET)
env.cr.commit()

Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
tmpl = Template.search([("default_code", "=", SKU)], limit=1)
v = Product.search([("default_code", "=", SKU)], limit=1)
print("CANCELLED ORDERS:", cancelled)
print("TRIM:", trim)
print(f"AFTER: on_hand={tmpl.qty_available} website={tmpl._rw_website_available_qty()}")
for lot in Lot.search([("product_id", "=", v.id)], order="name"):
    q = Quant.search(
        [("product_id", "=", v.id), ("lot_id", "=", lot.id), ("quantity", ">", 0)],
        limit=1,
    )
    if q:
        print(f"  IN STOCK: {lot.name}")
print("ACTIVE ORDERS:", SO.search_count([("state", "!=", "cancel")]))
