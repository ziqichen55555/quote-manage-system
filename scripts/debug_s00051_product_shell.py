# -*- coding: utf-8 -*-
"""Diagnose S00051 / PC1ACZL4 — why product missing from Add products."""
SERIAL = "PC1ACZL4"
ORDER = "S00051"

SO = env["sale.order"].sudo().search([("name", "=", ORDER)], limit=1)
if not SO:
    print(f"Order {ORDER} not found")
else:
    print("=" * 72)
    print(f"Order {SO.name}  state={SO.state}  delivery={SO.delivery_status}")
    print(f"Customer: {SO.partner_id.name}")
    print(f"Created: {SO.create_date}")
    print()
    for line in SO.order_line:
        p = line.product_id
        tmpl = p.product_tmpl_id
        print(f"Line: {line.name[:60]}")
        print(f"  product_id={p.id}  variant_code={p.default_code!r}")
        print(f"  template_id={tmpl.id}  template_code={tmpl.default_code!r}")
        print(f"  sale_ok={tmpl.sale_ok}  published={tmpl.is_published}  active={tmpl.active}")
        print(f"  tracking={tmpl.tracking}  type={tmpl.type}")
        print(f"  qty={line.product_uom_qty}  delivered={line.qty_delivered}")
        for ml in line.move_ids.move_line_ids.filtered(lambda x: x.lot_id):
            print(f"  serial={ml.lot_id.name}  picking={ml.picking_id.name}  state={ml.picking_id.state}")

Lot = env["stock.lot"].sudo()
lots = Lot.search([("name", "=ilike", SERIAL)])
print()
print("=" * 72)
print(f"Lot search for {SERIAL}: {len(lots)}")
for lot in lots:
    p = lot.product_id
    tmpl = p.product_tmpl_id
    print(f"  lot_id={lot.id}  product={p.display_name}")
    print(f"    variant_code={p.default_code!r}  template_code={tmpl.default_code!r}")
    print(f"    sale_ok={tmpl.sale_ok}  published={tmpl.is_published}  created={tmpl.create_date}")

PT = env["product.template"].sudo().with_context(active_test=False)
# Recently created products (last 3 days)
from datetime import datetime, timedelta
since = datetime.now() - timedelta(days=3)
recent = PT.search([("create_date", ">=", since.strftime("%Y-%m-%d %H:%M:%S"))], order="create_date desc", limit=25)
print()
print("=" * 72)
print(f"Products created in last 3 days: {len(recent)}")
for t in recent:
    code = (t.default_code or "").strip()
    name = (t.name or "")[:50]
    print(
        f"  id={t.id}  {t.create_date}  code={code!r}  "
        f"sale_ok={t.sale_ok}  pub={t.is_published}  name={name}"
    )

# T490s CMOSP family
print()
print("=" * 72)
print("T490s 256G BT70 CMOSP templates:")
for t in PT.search([("default_code", "ilike", "20NYS4CP00%256G%BT70%CMOSP")]):
    print(
        f"  id={t.id}  code={t.default_code!r}  sale_ok={t.sale_ok}  "
        f"pub={t.is_published}  on_hand={t.qty_available}  name={t.name[:45]}"
    )

print()
print("Done.")
