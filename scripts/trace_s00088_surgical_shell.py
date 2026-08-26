# -*- coding: utf-8 -*-
"""Surgical trace for S00088 - Investigation of SNs in stock."""
name = "S00088"
SO = env["sale.order"].sudo()
order = SO.search([("name", "=", name)], limit=1)

if not order:
    print(f"Order {name} not found.")
else:
    print(f"Order: {order.name}, State: {order.state}, Date: {order.date_order}")
    
    # 1. Check Pickings
    print("\nPickings:")
    for pick in order.picking_ids:
        print(f"  - {pick.name}: State={pick.state}, Type={pick.picking_type_id.code}, DateDone={pick.date_done}")
        for ml in pick.move_line_ids:
            if ml.lot_id:
                # Check current stock for this SN
                quants = env["stock.quant"].sudo().search([("lot_id", "=", ml.lot_id.id), ("quantity", ">", 0)])
                stock_locs = [f"{q.location_id.display_name}({q.quantity:g})" for q in quants]
                print(f"    SN: {ml.lot_id.name}, Qty In Move: {ml.quantity:g}, Current Stock: {', '.join(stock_locs) or 'None'}")

    # 2. Check recent chatter (very limited)
    print("\nRecent Chatter (last 5):")
    messages = env["mail.message"].sudo().search([
        ("model", "=", "sale.order"),
        ("res_id", "=", order.id)
    ], limit=5, order="id desc")
    for m in messages:
        author = m.author_id.name or m.email_from
        body = (m.body or "")[:100].replace('\n', ' ')
        print(f"  - {m.date} [{author}]: {body}")

print("\nDone.")
