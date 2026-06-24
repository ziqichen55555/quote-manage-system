# -*- coding: utf-8 -*-
"""Odoo shell: diagnose LAT3301 serial stock. Usage: odoo shell -d DB < scripts/debug_lat3301_serial_shell.py"""
SKU = "LAT3301"
Lot = env["stock.lot"].sudo()
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Importer = env["product.csv.importer"].sudo()

tmpl = Template.search([("default_code", "=", SKU)], limit=1)
if not tmpl:
    tmpl = Template.search([("default_code", "=ilike", f"RW-{SKU}")], limit=1)
print("TEMPLATE:", tmpl.id, tmpl.default_code, "tracking=", tmpl.tracking, "qty=", tmpl.qty_available)

variants = Product.search(
    [
        "|",
        ("default_code", "=", SKU),
        ("product_tmpl_id", "=", tmpl.id if tmpl else 0),
    ]
)
print("VARIANTS:", len(variants))
for v in variants:
    lots = Lot.search([("product_id", "=", v.id)])
    on_hand = v.qty_available
    quants = Quant.search(
        [
            ("product_id", "=", v.id),
            ("location_id.usage", "=", "internal"),
            ("quantity", ">", 0),
        ]
    )
    no_lot = quants.filtered(lambda q: not q.lot_id)
    with_lot = quants.filtered(lambda q: q.lot_id)
    print(
        f"  id={v.id} code={v.default_code!r} active={v.active} "
        f"qty={on_hand} lots={len(lots)} quants_no_lot={sum(no_lot.mapped('quantity'))} "
        f"quants_with_lot={len(with_lot)}"
    )
    for lot in lots[:15]:
        q = Quant.search(
            [
                ("product_id", "=", v.id),
                ("lot_id", "=", lot.id),
                ("quantity", ">", 0),
            ],
            limit=1,
        )
        print(f"    lot {lot.name!r} on_hand={q.quantity if q else 0}")

print("\nREPAIR (dry run info) — run repair_serial_stock_quants to fix lot-less quants:")
if hasattr(Importer, "repair_serial_stock_quants"):
    print(Importer.repair_serial_stock_quants(SKU))
