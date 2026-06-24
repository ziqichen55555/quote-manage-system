# -*- coding: utf-8 -*-
"""HP / Panasonic / Toughbook / KBC products on prod copy."""
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()

keys = ["CF", "FZ", "TOUGH", "T1D", "HP", "KBC", "PANASONIC", "ABG", "26D", "3FF"]
tmpls = Template.search([("type", "=", "product"), ("active", "=", True)])
for t in tmpls.sorted(key=lambda x: x.default_code or x.name):
    blob = f"{t.default_code or ''} {t.name}".upper()
    if not any(k in blob for k in keys):
        continue
    print(f"\n{t.default_code!r} track={t.tracking} on={t.qty_available} virt={t.virtual_available}")
    print(f"  name: {t.name}")
    for v in t.product_variant_ids:
        quants = Quant.search([("product_id", "=", v.id), ("quantity", ">", 0), ("location_id.usage", "=", "internal")])
        for q in quants:
            sn = q.lot_id.name if q.lot_id else "(no lot)"
            print(f"    qty={q.quantity} lot={sn!r} reserved={q.reserved_quantity}")
