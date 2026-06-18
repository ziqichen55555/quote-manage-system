# -*- coding: utf-8 -*-
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
StockQuant = env["stock.quant"].sudo()

serial_templates = Template.search([("tracking", "=", "serial")])
laptop_no_track = Template.search([
    ("tracking", "=", "none"),
    ("categ_id.name", "ilike", "laptop"),
])
variants = Product.search([])
on_hand = StockQuant.search([("location_id.usage", "=", "internal"), ("quantity", ">", 0)])
on_hand_qty = sum(on_hand.mapped("quantity"))

recent = Template.search([], order="write_date desc", limit=5)
print("SERIAL_TRACKING_TEMPLATES:", len(serial_templates))
print("LAPTOP_NO_TRACKING:", len(laptop_no_track))
print("TOTAL_VARIANTS:", len(variants))
print("ON_HAND_INTERNAL_QTY:", int(on_hand_qty))
print("RECENT_TEMPLATES:")
for t in recent:
    print(f"  {t.default_code or '-'} | {t.name[:60]} | track={t.tracking} | qty={t.qty_available}")
