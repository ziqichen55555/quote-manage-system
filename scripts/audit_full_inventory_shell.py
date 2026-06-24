# -*- coding: utf-8 -*-
"""Full inventory health on prod copy DB."""
import re

Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SO = env["sale.order"].sudo()

AUTO_SN = re.compile(r"^S/N-([A-Z0-9-]+)-\d{3}$", re.I)

serial_tmpls = Template.search(
    [("tracking", "=", "serial"), ("type", "=", "product"), ("active", "=", True)]
)
print(f"=== SERIAL PRODUCTS WITH STOCK ({len(serial_tmpls)} tracked) ===\n")

issues_no_lot = []
issues_mixed = []
issues_auto_only = []
ok = []

for tmpl in serial_tmpls.sorted(key=lambda t: (t.default_code or "", t.name)):
    on_hand = tmpl.qty_available
    if on_hand <= 0:
        continue
    variants = tmpl.product_variant_ids.filtered(lambda v: v.active)
    no_lot = auto_qty = real_qty = 0.0
    real_names, auto_names = [], []
    for v in variants:
        for q in Quant.search(
            [
                ("product_id", "=", v.id),
                ("location_id.usage", "=", "internal"),
                ("quantity", ">", 0),
            ]
        ):
            if not q.lot_id:
                no_lot += q.quantity
            elif AUTO_SN.match(q.lot_id.name):
                auto_qty += q.quantity
                auto_names.append(q.lot_id.name)
            else:
                real_qty += q.quantity
                real_names.append(q.lot_id.name)
    open_qty = sum(
        env["sale.order.line"]
        .sudo()
        .search(
            [
                ("product_id.product_tmpl_id", "=", tmpl.id),
                ("order_id.state", "=", "sale"),
            ]
        )
        .mapped("product_uom_qty")
    )
    code = tmpl.default_code or str(tmpl.id)
    row = {
        "code": code,
        "name": tmpl.name[:45],
        "on_hand": on_hand,
        "no_lot": no_lot,
        "real": real_qty,
        "auto": auto_qty,
        "open_so": open_qty,
        "free_est": on_hand - open_qty,
        "real_sample": real_names[:2],
        "auto_sample": auto_names[:2],
    }
    if no_lot > 0:
        issues_no_lot.append(row)
    elif auto_qty > 0 and real_qty > 0:
        issues_mixed.append(row)
    elif auto_qty > 0:
        issues_auto_only.append(row)
    elif real_qty > 0:
        ok.append(row)

print(f"OK (real SN only): {len(ok)}")
for r in ok:
    print(f"  {r['code']:16} on={r['on_hand']:4.0f} open_SO={r['open_so']:3.0f} free~{r['free_est']:4.0f}  {r['name']}")

print(f"\nNO LOT (broken serial stock): {len(issues_no_lot)}")
for r in issues_no_lot:
    print(f"  {r['code']:16} on={r['on_hand']:4.0f} NO_LOT={r['no_lot']:4.0f} open_SO={r['open_so']:3.0f}  {r['name']}")

print(f"\nAUTO S/N-* only: {len(issues_auto_only)}")
for r in issues_auto_only:
    print(f"  {r['code']:16} on={r['on_hand']:4.0f}  {r['auto_sample']}")

print(f"\nMIXED real+auto: {len(issues_mixed)}")
for r in issues_mixed:
    print(f"  {r['code']:16} on={r['on_hand']:4.0f} real={r['real']} auto={r['auto']}")

non_serial = Template.search(
    [
        ("tracking", "!=", "serial"),
        ("type", "=", "product"),
        ("active", "=", True),
        ("qty_available", ">", 0),
    ]
)
print(f"\n=== NON-SERIAL WITH STOCK: {len(non_serial)} ===")
for t in non_serial.sorted(key=lambda x: x.default_code or x.name)[:30]:
    print(f"  {t.default_code or '-':16} on={t.qty_available:4.0f} track={t.tracking}  {t.name[:40]}")

print(f"\n=== ORDERS ===")
print(f"  sale: {SO.search_count([('state', '=', 'sale')])}")
print(f"  draft: {SO.search_count([('state', '=', 'draft')])}")
print(f"  cancel: {SO.search_count([('state', '=', 'cancel')])}")
