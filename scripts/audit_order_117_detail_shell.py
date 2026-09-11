# -*- coding: utf-8 -*-
order = env['sale.order'].sudo().search([('name', '=', 'S00117')], limit=1)

if not order:
    print("Order S00117 not found.")
else:
    print(f"Order: {order.name}, State: {order.state}, Total: {order.amount_total}")
    print("Lines:")
    for line in order.order_line:
        print(f"ID: {line.id}, Product: {line.product_id.display_name}")
        print(f"  Qty: Ordered={line.product_uom_qty}, Delivered={line.qty_delivered}, Invoiced={line.qty_invoiced}")
        print(f"  Price: Unit={line.price_unit}, Subtotal={line.price_subtotal}, Tax={line.tax_id.mapped('name')}")
    
    print("\nInvoices:")
    for inv in order.invoice_ids:
        print(f"Invoice: {inv.name}, State: {inv.state}, Amount Total: {inv.amount_total}, Amount Residual: {inv.amount_residual}")
        for inv_line in inv.invoice_line_ids:
            print(f"  Line: {inv_line.product_id.display_name}, Qty: {inv_line.quantity}, Price: {inv_line.price_unit}")
