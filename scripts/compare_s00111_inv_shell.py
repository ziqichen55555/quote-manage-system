# -*- coding: utf-8 -*-
"""Compare S00111 total vs INV/2026/00064 total and check for missing lines."""
order = env['sale.order'].sudo().search([('name', '=', 'S00111')], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', 'INV/2026/00064')], limit=1)

if order and invoice:
    print(f"Order {order.name} Total: {order.amount_total:g}")
    print(f"Invoice {invoice.name} Total: {invoice.amount_total:g}")
    
    print("\n--- Sale Order Lines ---")
    for line in order.order_line:
        print(f"Product: {line.product_id.display_name} | Qty: {line.product_uom_qty:g} | Subtotal: {line.price_subtotal:g}")
        
    print("\n--- Invoice Lines ---")
    for line in invoice.invoice_line_ids:
        print(f"Product: {line.product_id.display_name} | Qty: {line.quantity:g} | Subtotal: {line.price_subtotal:g}")

print("\nDone.")
