# -*- coding: utf-8 -*-
"""Check tax details for S00111 and INV/2026/00064."""
order = env['sale.order'].sudo().search([('name', '=', 'S00111')], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', 'INV/2026/00064')], limit=1)

if order and invoice:
    print(f"=== Order: {order.name} ===")
    print(f"Untaxed Amount: {order.amount_untaxed}")
    print(f"Tax Amount: {order.amount_tax}")
    print(f"Total Amount: {order.amount_total}")
    
    print(f"\n=== Invoice: {invoice.name} ===")
    print(f"Untaxed Amount: {invoice.amount_untaxed}")
    print(f"Tax Amount: {invoice.amount_tax}")
    print(f"Total Amount: {invoice.amount_total}")
    
    print("\n--- Invoice Tax Lines ---")
    for tax_line in invoice.line_ids.filtered(lambda l: l.display_type == 'tax'):
        print(f"Tax: {tax_line.name} | Amount: {tax_line.price_subtotal}")

print("\nDone.")
