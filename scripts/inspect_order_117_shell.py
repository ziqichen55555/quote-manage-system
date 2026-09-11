# -*- coding: utf-8 -*-
order = env['sale.order'].sudo().search([('name', '=', 'S00117')], limit=1)

if not order:
    print("Order S00117 not found.")
else:
    print(f"Order: {order.name} (ID: {order.id})")
    print(f"Total: {order.amount_total}")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print("-" * 40)
    for line in order.order_line:
        print(f"Line {line.id}: {line.product_id.name}")
        print(f"  Qty: {line.product_uom_qty}, Price: {line.price_unit}")
        print(f"  Delivered: {line.qty_delivered}, Invoiced: {line.qty_invoiced}")
        print("-" * 20)
    
    invoices = order.invoice_ids
    print(f"Invoices count: {len(invoices)}")
    for inv in invoices:
        print(f"Invoice {inv.name}: {inv.state}, Total: {inv.amount_total}")
