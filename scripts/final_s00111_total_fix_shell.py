# -*- coding: utf-8 -*-
"""Surgical fix for INV/2026/00064 to match exactly $1100."""
DRY_RUN = False
invoice_name = 'INV/2026/00064'
invoice = env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)

if not invoice:
    print(f"Invoice {invoice_name} not found.")
else:
    print(f"=== Correcting Invoice {invoice.name} ===")
    
    # 1. Fix T480s price to $140
    t480s_line = invoice.invoice_line_ids.filtered(lambda l: 'T480s' in l.name)
    if t480s_line:
        print(f"Updating T480s line {t480s_line.id} price to 140")
        t480s_line.write({'price_unit': 140.0})
    
    # 2. Check and remove any duplicate/wrong shipping lines
    # Based on sum: 520 (T490s) + 340 (T14s) + 140 (T480s) = 1000.
    # To get to 1100 total with 10% tax, we need untaxed to be 1000.
    # So shipping must be 0 if the products already sum to 1000.
    
    shipping_lines = invoice.invoice_line_ids.filtered(lambda l: 'Shipping' in l.name)
    for sl in shipping_lines:
        print(f"Removing shipping line {sl.id} (Price: {sl.price_unit}) to match SO structure")
        sl.unlink()
        
    # 3. Force recompute
    invoice._compute_amount()
    print(f"New Untaxed: {invoice.amount_untaxed}")
    print(f"New Tax: {invoice.amount_tax}")
    print(f"New Total: {invoice.amount_total}")
    
    if not DRY_RUN:
        env.cr.commit()
        print("Changes COMMITTED.")

print("\nDone.")
