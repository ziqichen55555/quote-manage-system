# -*- coding: utf-8 -*-
"""Check contents of invoice INV/2026/00064 for order S00111."""
invoice_name = 'INV/2026/00064'
invoice = env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)

if not invoice:
    print(f"Invoice {invoice_name} not found.")
else:
    print(f"=== Invoice Details: {invoice.name} ===")
    print(f"State: {invoice.state}")
    print(f"Total Amount: {invoice.amount_total:g}")
    print(f"Partner: {invoice.partner_id.name}")
    
    print("\n--- Invoice Lines ---")
    for line in invoice.invoice_line_ids:
        print(f"Product: {line.product_id.display_name}")
        print(f"  - Quantity: {line.quantity:g}")
        print(f"  - Price Unit: {line.price_unit:g}")
        print(f"  - Subtotal: {line.price_subtotal:g}")

print("\nDone.")
