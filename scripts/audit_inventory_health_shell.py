# -*- coding: utf-8 -*-
"""Inventory health report — serial tracking vs lots, duplicates, order locks."""
import re

Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SO = env["sale.order"].sudo()

AUTO_SN = re.compile(r"^S/N-([A-Z0-9-]+)-\d{3}$", re.I)

issues = []
serial_tmpls = Template.search([("tracking", "=", "serial"), ("type", "=", "product"), ("active", "=", True)])
print(f"Serial-tracked active products: {len(serial_tmpls)}\n")

for tmpl in serial_tmpls.sorted(key=lambda t: t.default_code or t.name):
    code = (tmpl.default_code or "").strip()
    on_hand = tmpl.qty_available
    if on_hand <= 0:
        continue
    variants = tmpl.product_variant_ids.filtered(lambda v: v.active)
    lot_qty = 0
    auto_qty = real_qty = 0
    no_lot_qty = 0
    real_names = []
    auto_names = []
    for v in variants:
        for q in Quant.search(
            [
                ("product_id", "=", v.id),
                ("location_id.usage", "=", "internal"),
                ("quantity", ">", 0),
            ]
        ):
            if not q.lot_id:
                no_lot_qty += q.quantity
            elif AUTO_SN.match(q.lot_id.name):
                auto_qty += q.quantity
                auto_names.append(q.lot_id.name)
            else:
                real_qty += q.quantity
                real_names.append(q.lot_id.name)
            lot_qty += q.quantity if q.lot_id else 0
    lot_qty = sum(
        Quant.search(
            [
                ("product_id", "in", variants.ids),
                ("location_id.usage", "=", "internal"),
                ("lot_id", "!=", False),
                ("quantity", ">", 0),
            ]
        ).mapped("quantity")
    )
    open_lines = env["sale.order.line"].sudo().search(
        [
            ("product_id.product_tmpl_id", "=", tmpl.id),
            ("order_id.state", "=", "sale"),
        ]
    )
    open_qty = sum(open_lines.mapped("product_uom_qty"))
    flags = []
    if open_qty > 0:
        flags.append(f"open_SO_qty={open_qty}")
    if no_lot_qty > 0:
        flags.append(f"NO_LOT qty={no_lot_qty}")
    if auto_qty > 0 and real_qty > 0:
        flags.append(f"MIXED auto={int(auto_qty)} real={int(real_qty)}")
    elif auto_qty > 0:
        flags.append(f"AUTO_ONLY n={int(auto_qty)}")
    if abs(on_hand - lot_qty) > 0.01 and no_lot_qty == 0:
        flags.append(f"on_hand={on_hand} lot_sum={lot_qty}")
    if not flags:
        continue
    print(f"[{code or tmpl.id}] {tmpl.name[:50]!r} on_hand={on_hand}")
    for f in flags:
        print(f"    ! {f}")
    if auto_names[:3]:
        print(f"    auto sample: {auto_names[:3]}")
    if real_names[:3]:
        print(f"    real sample: {real_names[:3]}")

print("\n=== SALE ORDERS (active) ===")
for o in SO.search([("state", "!=", "cancel")], order="name"):
    print(f"  {o.name} state={o.state} partner={o.partner_id.name!r} total={o.amount_total}")

print("\n=== RW- duplicate templates (sample) ===")
rw = Template.search([("default_code", "=like", "RW-%"), ("active", "=", True)], limit=20)
for t in rw:
    canon = (t.default_code or "")[3:]
    other = Template.search([("default_code", "=", canon), ("id", "!=", t.id)], limit=1)
    if other:
        print(f"  dup: {t.default_code} ({t.qty_available}) vs {other.default_code} ({other.qty_available})")
