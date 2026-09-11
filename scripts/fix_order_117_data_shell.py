# -*- coding: utf-8 -*-
order = env['sale.order'].sudo().search([('name', '=', 'S00117')], limit=1)

if not order:
    print("Order S00117 not found.")
else:
    print(f"Fixing Order: {order.name}")
    
    # Line 230 is the one with 4 delivered and 35.0 price
    line_to_fix = order.order_line.filtered(lambda l: l.id == 230)
    if line_to_fix:
        print(f"Updating line {line_to_fix.id} price to 0.0 and qty to 4.0")
        line_to_fix.write({
            'price_unit': 0.0,
            'product_uom_qty': 4.0,
        })
    
    # Line 228 was 1 qty at 0 price invoiced. It's redundant but already on a posted invoice.
    # We will just leave it.
    
    # Now trigger invoice creation for the 0.0 price lines to clear the status
    # This will create a $0 invoice for the 4 adapters.
    print("Creating $0 invoice for adapters...")
    new_inv = order._create_invoices()
    if new_inv:
        new_inv.action_post()
        print(f"Created and posted $0 invoice: {new_inv.name}")
    
    print(f"New Order Total: {order.amount_total}")
    print("Fix completed.")

env.cr.commit()
