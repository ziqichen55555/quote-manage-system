# -*- coding: utf-8 -*-
"""Zero phantom stock on sold unit R913RZGT (delivered on obsolete BT70 SKU)."""
DRY_RUN = False
SKU = "20TJS5WW00-BT70-CMOSP"
SERIAL = "R913RZGT"

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)

tmpl, code = Importer._find_product_by_sku(SKU)
print("BEFORE:", code, "on_hand=", tmpl.qty_available, "published=", tmpl.is_published)

# Delivered via WH/OUT/00020 on 20TJS5WW00-BT70 — CMOSP +1 is phantom.
if not DRY_RUN:
    result = Importer.sync_serial_stock_allowlist(code, [])
    tmpl.invalidate_recordset()
    tmpl.write({"website_published": False, "sale_ok": False})
    env.cr.commit()
    print("sync:", result)
else:
    print("DRY_RUN only")

tmpl.invalidate_recordset()
print("AFTER:", code, "on_hand=", tmpl.qty_available, "published=", tmpl.is_published)
