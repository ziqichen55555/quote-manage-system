# -*- coding: utf-8 -*-
# NO def run(env) - odoo shell executes top-level code directly
order = env['sale.order'].sudo().search([('name', 'ilike', '117')], limit=1)

if not order:
    print(f"Order matching '117' not found.")
else:
    print(f"Order: {order.name} (ID: {order.id})")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print(f"Partner: {order.partner_id.name}")
    print("-" * 40)
    
    for line in order.order_line:
        print(f"Product: {line.product_id.display_name}")
        print(f"  Qty Ordered: {line.product_uom_qty}")
        print(f"  Qty Delivered: {line.qty_delivered}")
        print(f"  Qty Invoiced: {line.qty_invoiced}")
        print(f"  Line Invoice Status: {line.invoice_status}")
        print(f"  Policy: {line.product_id.invoice_policy}")
        if line.product_id.type == 'service':
            print(f"  Upsell Threshold: {line.product_id.service_upsell_threshold}")
        print("-" * 20)
