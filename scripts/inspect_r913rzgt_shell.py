# -*- coding: utf-8 -*-
SERIAL = "R913RZGT"
Lot = env["stock.lot"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

print("=== Lots named", SERIAL, "===")
for lot in Lot.search([("name", "=", SERIAL)]):
    tmpl = lot.product_id.product_tmpl_id
    rows = Quant.search([("lot_id", "=", lot.id), ("quantity", "!=", 0)])
    print(
        f"  lot={lot.id} sku={lot.product_id.default_code} "
        f"active={tmpl.active} on_hand_tmpl={tmpl.qty_available}"
    )
    for q in rows:
        print(f"    {q.location_id.complete_name}: {q.quantity}")

print("\n=== 20TJS5WW00 family ===")
for tmpl in PT.search([("default_code", "=ilike", "20TJS5WW00%")], order="default_code"):
    wh_sns = []
    for v in tmpl.product_variant_ids:
        for lot in Lot.search([("product_id", "=", v.id), ("name", "=", SERIAL)]):
            q = sum(
                Quant.search(
                    [
                        ("lot_id", "=", lot.id),
                        ("location_id", "child_of", WH.lot_stock_id.id),
                        ("quantity", ">", 0),
                    ]
                ).mapped("quantity")
            ) if WH else 0
            wh_sns.append(f"WH={q}")
    flag = " <--" if wh_sns else ""
    print(
        f"  {tmpl.default_code} active={tmpl.active} on_hand={tmpl.qty_available}{flag} {wh_sns}"
    )
print("Done.")
