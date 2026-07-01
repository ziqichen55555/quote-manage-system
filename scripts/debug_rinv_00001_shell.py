# -*- coding: utf-8 -*-
refs = ["INV/2026/00007", "RINV/2026/00001"]
Move = env["account.move"].sudo()
SO = env["sale.order"].sudo().search([("name", "=", "S00030")], limit=1)

for name in refs:
    m = Move.search([("name", "=", name)], limit=1)
    print("=" * 72)
    if not m:
        print(f"{name}: NOT FOUND")
        continue
    print(f"{name}  id={m.id}  type={m.move_type}")
    print(f"  state={m.state}  payment_state={m.payment_state}")
    print(f"  partner={m.partner_id.name}  amount={m.amount_total}")
    print(f"  reversed_entry_id={m.reversed_entry_id.name if m.reversed_entry_id else '-'}")
    print(f"  reversal_move_id={m.reversal_move_id.name if m.reversal_move_id else '-'}")
    for line in m.invoice_line_ids[:3]:
        print(f"  line: {line.product_id.default_code or '-'}  {line.name[:50]}")

if SO:
    print()
    print("=" * 72)
    print(f"S00030  state={SO.state}  delivery={SO.delivery_status}")
    print(f"  invoice_ids: {SO.invoice_ids.mapped('name')}")
    print(f"  invoice_status: {SO.invoice_status}")
    for line in SO.order_line:
        print(f"  SO line: {line.product_id.default_code}  invoiced={line.qty_invoiced}  delivered={line.qty_delivered}")

print()
print("Done.")
