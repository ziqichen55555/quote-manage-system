# -*- coding: utf-8 -*-
"""Verify the final state of S00111 after correction."""
order_name = 'S00111'
order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)

if not order:
    print(f"Order {order_name} not found.")
else:
    print(f"=== Final State of {order.name} ===")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print(f"Total Amount: {order.amount_total}")
    
    print("\n--- Order Lines ---")
    for line in order.order_line:
        print(f"Product: {line.product_id.display_name}")
        print(f"  - Ordered: {line.product_uom_qty:g}, Delivered: {line.qty_delivered:g}, Invoiced: {line.qty_invoiced:g}")
        print(f"  - Price: {line.price_unit:g}, Subtotal: {line.price_subtotal:g}")

    print("\n--- Invoices ---")
    for inv in order.invoice_ids:
        print(f"Invoice: {inv.name} | Total: {inv.amount_total:g} | State: {inv.state}")

print("\nDone.")
