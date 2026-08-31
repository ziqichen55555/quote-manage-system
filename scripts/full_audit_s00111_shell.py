# -*- coding: utf-8 -*-
"""Full line audit for S00111 and INV/2026/00064 including shipping and taxes."""
order = env['sale.order'].sudo().search([('name', '=', 'S00111')], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', 'INV/2026/00064')], limit=1)

if order and invoice:
    print(f"=== Order: {order.name} ===")
    print(f"Total: {order.amount_total:g}, Untaxed: {order.amount_untaxed:g}, Tax: {order.amount_tax:g}")
    for line in order.order_line:
        print(f"Line: {line.name} | Product: {line.product_id.display_name} | Qty: {line.product_uom_qty:g} | Subtotal: {line.price_subtotal:g}")
        
    print(f"\n=== Invoice: {invoice.name} ===")
    print(f"Total: {invoice.amount_total:g}, Untaxed: {invoice.amount_untaxed:g}, Tax: {invoice.amount_tax:g}")
    for line in invoice.invoice_line_ids:
        print(f"Line: {line.name} | Product: {line.product_id.display_name} | Qty: {line.quantity:g} | Subtotal: {line.price_subtotal:g}")

print("\nDone.")
