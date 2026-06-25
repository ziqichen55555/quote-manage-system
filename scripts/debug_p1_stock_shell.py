# -*- coding: utf-8 -*-
Template = env["product.template"].sudo()
Product = env["product.product"].sudo()
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
Website = env["website"].get_current_website()
wh = Website._get_warehouse_available()
for code in ["20TJS5WW00", "20TJS5WW00-BT70", "20TJS5WW00-BTU70"]:
    tmpl = Template.with_context(active_test=False).search(
        [("default_code", "=", code)], limit=1
    )
    print("===", code, "found", bool(tmpl), "===")
    if not tmpl:
        continue
    print(
        "id",
        tmpl.id,
        "name",
        tmpl.name,
        "published",
        tmpl.website_published,
        "active",
        tmpl.active,
    )
    print(
        "qty_available",
        tmpl.qty_available,
        "website_qty",
        tmpl._rw_website_available_qty(),
    )
    for v in tmpl.product_variant_ids:
        fq = v.with_context(warehouse=wh).free_qty
        print(
            " variant",
            v.id,
            v.default_code,
            "active",
            v.active,
            "qty",
            v.qty_available,
            "free_qty",
            fq,
        )
        lots = Lot.search([("product_id", "=", v.id)])
        for lot in lots:
            q = Quant.search(
                [
                    ("product_id", "=", v.id),
                    ("lot_id", "=", lot.id),
                    ("location_id.usage", "=", "internal"),
                ]
            )
            print("  lot", lot.name, "qty", sum(q.mapped("quantity")))
for l in Lot.search([("name", "=", "R913RZGT")]):
    p = l.product_id
    print(
        "SN R913RZGT ->",
        p.default_code,
        "tmpl",
        p.product_tmpl_id.default_code,
        "on_hand",
        p.qty_available,
    )
