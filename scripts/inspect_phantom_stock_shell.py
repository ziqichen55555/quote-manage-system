# -*- coding: utf-8 -*-
"""Inspect nonzero quants on obsolete / keeper refurb SKUs."""
SKUS = [
    "20L8SDCE00",
    "20NYS4CP00-8G-256G-T-BT70",
    "20NYS4CP00-8G-512G-T-BT70",
    "20NYS4CP00-8G-256G-N",
]

PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()

for sku in SKUS:
    tmpls = PT.search([("default_code", "=ilike", sku)])
    print("=" * 60, sku, "templates=", tmpls.ids)
    for tmpl in tmpls:
        print(
            f"  tmpl={tmpl.id} code={tmpl.default_code} active={tmpl.active} "
            f"on_hand={tmpl.qty_available}"
        )
        for variant in tmpl.product_variant_ids:
            quants = Quant.search(
                [("product_id", "=", variant.id), ("quantity", "!=", 0)]
            )
            for q in quants:
                sn = q.lot_id.name if q.lot_id else "(no-lot)"
                print(
                    f"    quant id={q.id} sn={sn} qty={q.quantity} "
                    f"loc={q.location_id.complete_name}"
                )
    print()

print("Done.")
