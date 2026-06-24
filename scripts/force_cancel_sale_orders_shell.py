# -*- coding: utf-8 -*-
"""Force-cancel sale orders stuck after action_cancel."""
SO = env["sale.order"].sudo()
AM = env["account.move"].sudo()

for order in SO.search([("state", "!=", "cancel")]):
    print(f"Force cancel {order.name} state={order.state}")
    for inv in order.invoice_ids.filtered(lambda m: m.state == "draft"):
        inv.button_cancel()
    for picking in order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")):
        picking.action_cancel()
    try:
        order.action_cancel()
    except Exception as exc:
        print(f"  action_cancel failed: {exc}")
    if order.state != "cancel":
        order.write({"state": "cancel"})
        print(f"  wrote state=cancel")

env.cr.commit()
print("Remaining active:", SO.search([("state", "!=", "cancel")]).mapped("name"))
