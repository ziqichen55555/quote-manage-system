# -*- coding: utf-8 -*-
"""Cancel every sale order (and open pickings). Run on prod shell after backup."""
SO = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()

cancelled_orders = []
skipped = []
errors = []

for order in SO.search([], order="name"):
    name = order.name
    try:
        if order.state == "cancel":
            skipped.append(name)
            continue
        for picking in order.picking_ids.filtered(
            lambda p: p.state not in ("done", "cancel")
        ):
            picking.action_cancel()
        if order.state in ("draft", "sent", "sale"):
            order.action_cancel()
        cancelled_orders.append(name)
    except Exception as exc:
        errors.append(f"{name}: {exc}")

# Orphan outgoing pickings (no SO link)
for picking in Picking.search(
    [("state", "not in", ("done", "cancel")), ("picking_type_code", "=", "outgoing")]
):
    if picking.sale_id and picking.sale_id.state != "cancel":
        continue
    try:
        picking.action_cancel()
        print(f"Cancelled orphan picking {picking.name}")
    except Exception as exc:
        errors.append(f"picking {picking.name}: {exc}")

env.cr.commit()
print("CANCELLED:", cancelled_orders)
print("ALREADY CANCEL:", skipped)
print("ERRORS:", errors)
print("REMAINING ORDERS:", SO.search_count([("state", "!=", "cancel")]))
