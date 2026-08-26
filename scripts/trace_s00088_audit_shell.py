# -*- coding: utf-8 -*-
"""Analyze S00088 lines vs delivery."""
name = "S00088"
order = env["sale.order"].sudo().search([("name", "=", name)], limit=1)

if not order:
    print(f"Order {name} not found.")
else:
    print(f"Order: {order.name}, State: {order.state}")
    for line in order.order_line.filtered(lambda l: not l.display_type):
        print(f"Product: {line.product_id.display_name}, Ordered: {line.product_uom_qty:g}, Delivered: {line.qty_delivered:g}")
    
    print("\nAll lots associated with this order's pickings:")
    for pick in order.picking_ids:
        print(f"Picking: {pick.name} ({pick.state})")
        for ml in pick.move_line_ids:
            if ml.lot_id:
                print(f"  - SN: {ml.lot_id.name}, Qty: {ml.quantity:g}")

    # Check if there are any lots with similar names that ARE in WH/Stock
    # Maybe the user is seeing a duplicate?
    sns = order.picking_ids.move_line_ids.lot_id.mapped('name')
    if sns:
        print("\nChecking for these SNs in internal locations (WH/Stock):")
        internal_locs = env['stock.location'].search([('usage', '=', 'internal')])
        quants = env['stock.quant'].search([
            ('lot_id.name', 'in', sns),
            ('location_id', 'child_of', internal_locs.ids),
            ('quantity', '>', 0)
        ])
        if quants:
            for q in quants:
                print(f"  FOUND IN STOCK: SN={q.lot_id.name}, Loc={q.location_id.display_name}, Qty={q.quantity:g}")
        else:
            print("  None found in internal stock.")
