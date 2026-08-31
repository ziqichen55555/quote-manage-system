# -*- coding: utf-8 -*-
"""Fix shipping amount on INV/2026/00064 to match S00111."""
invoice_name = 'INV/2026/00064'
invoice = env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)

if not invoice:
    print(f"Invoice {invoice_name} not found.")
else:
    print(f"=== Correcting Shipping on {invoice.name} ===")
    
    # Find the shipping line (usually based on product or name)
    shipping_line = invoice.invoice_line_ids.filtered(lambda l: 'Shipping' in l.name or (l.product_id and 'Shipping' in l.product_id.name))
    
    if shipping_line:
        print(f"Found Shipping Line ID: {shipping_line.id}")
        print(f"Current Price: {shipping_line.price_unit}")
        
        # Update to $100
        shipping_line.write({'price_unit': 100.0})
        print(f"Updated Shipping Price to 100.0")
        
        # Re-check total
        invoice._compute_amount()
        print(f"New Invoice Total: {invoice.amount_total}")
        
        # Post note
        invoice.message_post(body="Backend correction: Adjusted shipping price from $150 to $100 to match Sales Order S00111.")
        
        print("\nCommitting changes...")
        env.cr.commit()
        print("Done.")
    else:
        print("Shipping line not found on invoice.")

print("\nDone.")
