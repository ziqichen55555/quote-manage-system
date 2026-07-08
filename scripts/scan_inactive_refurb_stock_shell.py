# -*- coding: utf-8 -*-
"""List inactive refurb serial SKUs with warehouse or net on_hand stock."""
cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

dom = [
    ("type", "=", "product"),
    ("tracking", "=", "serial"),
    ("public_categ_ids", "in", [cat_l, cat_d]),
    ("active", "=", False),
]

hits = []
for tmpl in PT.search(dom, order="default_code"):
    code = (tmpl.default_code or "").upper()
    if code.endswith("-CMOSP") or code.endswith("-CMOSFL"):
        continue
    oh = float(tmpl.qty_available or 0)
    wh_qty = 0.0
    wh_sns = []
    if WH:
        for variant in tmpl.product_variant_ids:
            for q in Quant.search(
                [
                    ("product_id", "=", variant.id),
                    ("location_id", "child_of", WH.lot_stock_id.id),
                    ("quantity", ">", 0),
                ]
            ):
                wh_qty += float(q.quantity)
                if q.lot_id:
                    wh_sns.append(q.lot_id.name)
    if oh != 0 or wh_qty > 0:
        hits.append((code or "(no code)", tmpl.id, tmpl.name, oh, wh_qty, len(wh_sns)))

print("Inactive obsolete refurb with stock:", len(hits))
for row in hits:
    print(
        f"  {row[0]} tmpl={row[1]} name={row[2]!r} "
        f"on_hand={row[3]} wh_qty={row[4]} wh_serials={row[5]}"
    )
print("Done.")
