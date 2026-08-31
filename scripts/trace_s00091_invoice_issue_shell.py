# -*- coding: utf-8 -*-
"""Investigate why S00091 cannot generate an invoice."""
order_name = 'S00091'
order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)

if not order:
    print(f"Order {order_name} not found.")
else:
    print(f"=== Audit for Sale Order: {order.name} ===")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print(f"Partner: {order.partner_id.name}")
    
    print("\n--- Order Lines ---")
    for line in order.order_line:
        if line.display_type:
            continue
        print(f"Product: {line.product_id.display_name}")
        print(f"  - Invoicing Policy: {line.product_id.invoice_policy}")
        print(f"  - Qty Ordered: {line.product_uom_qty:g}")
        print(f"  - Qty Delivered: {line.qty_delivered:g}")
        print(f"  - Qty Invoiced: {line.qty_invoiced:g}")
        print(f"  - To Invoice: {line.qty_to_invoice:g}")
        print(f"  - Price Unit: {line.price_unit:g}")

    print("\n--- Pickings ---")
    for pick in order.picking_ids:
        print(f"  - Picking: {pick.name} | State: {pick.state} | Type: {pick.picking_type_id.name}")

    print("\n--- Invoices ---")
    for inv in order.invoice_ids:
        print(f"  - Invoice: {inv.name or inv.id} | State: {inv.state} | Payment Status: {inv.payment_state}")

    # Check for potential blockages
    if order.invoice_status == 'no':
        print("\nPotential Reason: Invoice Status is 'no'. This usually means nothing is ready to be invoiced based on the policy (Ordered vs Delivered).")
    elif order.invoice_status == 'invoiced':
        print("\nPotential Reason: Order is already fully invoiced.")

print("\nDone.")
