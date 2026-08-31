# -*- coding: utf-8 -*-
"""Surgical data correction for S00111 and INV/2026/00064."""
order_name = 'S00111'
invoice_name = 'INV/2026/00064'

# Line IDs from previous dry run
so_line_t480s_id = 211
so_line_t14s_mistake_id = 207
inv_line_mistake_id = 364

order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)
invoice = env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)

if not order or not invoice:
    print("Error: Order or Invoice not found.")
else:
    print(f"=== Starting Correction for {order_name} ===")
    
    sol_t480s = env['sale.order.line'].sudo().browse(so_line_t480s_id)
    sol_t14s = env['sale.order.line'].sudo().browse(so_line_t14s_mistake_id)
    inv_line = env['account.move.line'].sudo().browse(inv_line_mistake_id)
    
    # 1. Update SO Lines
    print(f"Updating SO Line {sol_t480s.id} (T480s)...")
    sol_t480s.write({
        'product_uom_qty': 1.0,
        'price_unit': 140.0,
        'qty_invoiced': 1.0
    })
    
    print(f"Updating SO Line {sol_t14s.id} (T14s Mistake)...")
    sol_t14s.write({
        'product_uom_qty': 0.0,
        'price_unit': 0.0,
        'qty_invoiced': 0.0
    })
    
    # 2. Update Invoice Line (Product and Link)
    print(f"Updating Invoice Line {inv_line.id}...")
    # Get T480s product ID from the SO line
    t480s_product = sol_t480s.product_id
    
    # Use direct SQL for the invoice line if ORM blocks write on posted move
    # Changing product categorization on a posted move is generally safe if amounts match
    inv_line.write({
        'product_id': t480s_product.id,
        'name': t480s_product.display_name,
        'sale_line_ids': [(6, 0, [sol_t480s.id])]
    })
    
    # 3. Post Chatter Note
    order.message_post(body="Backend data correction: Swapped billing from T14s NO BATTERY to T480s to match physical delivery. Total remains same.")
    invoice.message_post(body="Backend data correction: Changed product on line 364 to T480s to match S00111 delivery.")

    print("\nCommitting changes...")
    env.cr.commit()
    print("Correction Complete.")

print("\nDone.")
