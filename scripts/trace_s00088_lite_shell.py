# -*- coding: utf-8 -*-
"""Ultra-lightweight trace for S00088."""
name = "S00088"
order = env["sale.order"].sudo().search([("name", "=", name)], limit=1)

if not order:
    print(f"Order {name} not found.")
else:
    print(f"Order: {order.name}, State: {order.state}")
    for pick in order.picking_ids:
        print(f"  Picking: {pick.name}, State: {pick.state}, Type: {pick.picking_type_id.code}")
        for ml in pick.move_line_ids:
            if ml.lot_id:
                quant = env["stock.quant"].sudo().search([("lot_id", "=", ml.lot_id.id), ("quantity", ">", 0)])
                stock_locs = [f"{q.location_id.display_name}({q.quantity:g})" for q in quant]
                print(f"    SN: {ml.lot_id.name}, Qty: {ml.quantity:g}, In Stock: {', '.join(stock_locs) or 'No'}")
