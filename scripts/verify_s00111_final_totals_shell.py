# -*- coding: utf-8 -*-
"""Final verification of S00111 and INV/2026/00064 totals."""
order = env['sale.order'].sudo().search([('name', '=', 'S00111')], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', 'INV/2026/00064')], limit=1)

if order and invoice:
    print(f"=== FINAL AUDIT ===")
    print(f"Order {order.name} Total: {order.amount_total}")
    print(f"Invoice {invoice.name} Total: {invoice.amount_total}")
    
    for line in invoice.invoice_line_ids:
        print(f"  - Line: {line.name} | Price: {line.price_unit} | Subtotal: {line.price_subtotal}")

print("\nDone.")
