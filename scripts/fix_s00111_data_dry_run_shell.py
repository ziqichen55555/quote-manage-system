# -*- coding: utf-8 -*-
"""Dry run to prepare data correction for S00111 and INV/2026/00064."""
order_name = 'S00111'
invoice_name = 'INV/2026/00064'

order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)

if not order or not invoice:
    print("Order or Invoice not found.")
else:
    print(f"=== S00111 Lines ===")
    for line in order.order_line:
        print(f"ID: {line.id} | Product: {line.product_id.display_name} | Qty: {line.product_uom_qty} | Price: {line.price_unit} | Delivered: {line.qty_delivered} | Invoiced: {line.qty_invoiced}")
        
    print(f"\n=== INV/2026/00064 Lines ===")
    for line in invoice.invoice_line_ids:
        print(f"ID: {line.id} | Product: {line.product_id.display_name} | Qty: {line.quantity} | Price: {line.price_unit} | Sale Line ID: {line.sale_line_ids.ids}")

    # Specific products to swap
    t480s_product_id = 2410 # Will verify in output
    t14s_no_battery_product_id = 2244 # Will verify in output
    
print("\nDone.")
