# -*- coding: utf-8 -*-
"""Ryan Kirby S00030 + S00033 — are these two real separate orders?"""
SO = env["sale.order"].sudo()
Move = env["account.move"].sudo()

for name in ("S00030", "S00033"):
    so = SO.search([("name", "=", name)], limit=1)
    print("=" * 72)
    print(f"{name}  created={so.create_date}  state={so.state}")
    print(f"  customer={so.partner_id.name}  total={so.amount_total}")
    print(f"  delivery={so.delivery_status}  invoice_status={so.invoice_status}")
    print(f"  salesperson={so.user_id.name if so.user_id else '-'}")
    print("  ORDER LINES:")
    for line in so.order_line:
        p = line.product_id
        print(
            f"    {p.default_code or '?':<40} qty={line.product_uom_qty}  "
            f"price={line.price_unit}  subtotal={line.price_subtotal}  "
            f"delivered={line.qty_delivered}  invoiced={line.qty_invoiced}"
        )
    print("  DELIVERIES:")
    for pick in so.picking_ids.sorted("name"):
        serials = pick.move_line_ids.filtered(lambda ml: ml.lot_id).mapped("lot_id.name")
        prods = pick.move_ids.mapped("product_id.default_code")
        print(f"    {pick.name}  state={pick.state}  products={prods}  serials={serials}")
    print("  INVOICES:")
    for inv in so.invoice_ids.sorted("name"):
        print(
            f"    {inv.name or 'DRAFT'}  type={inv.move_type}  state={inv.state}  "
            f"total={inv.amount_total}  payment={inv.payment_state}"
        )
        for line in inv.invoice_line_ids:
            print(f"      inv line: {line.product_id.default_code}  {line.name[:50]}")

print()
print("Done.")
