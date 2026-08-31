# -*- coding: utf-8 -*-
"""Investigate why S00111 cannot generate an invoice."""
order_name = 'S00111'

print(f"=== Investigating Invoicing Issue for {order_name} ===")

order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)

if not order:
    print(f"Order {order_name} not found.")
else:
    print(f"Order: {order.name}")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print(f"Partner: {order.partner_id.name}")
    
    print("\n--- Order Lines ---")
    for line in order.order_line.filtered(lambda l: not l.display_type):
        print(f"Product: {line.product_id.display_name}")
        print(f"  - Ordered Qty: {line.product_uom_qty:g}")
        print(f"  - Delivered Qty: {line.qty_delivered:g}")
        print(f"  - Invoiced Qty: {line.qty_invoiced:g}")
        print(f"  - To Invoice Qty: {line.qty_to_invoice:g}")
        print(f"  - Invoice Policy: {line.product_id.invoice_policy}")
        print(f"  - Price Unit: {line.price_unit:g}")

    print("\n--- Related Pickings ---")
    for pick in order.picking_ids:
        print(f"Picking: {pick.name} | State: {pick.state} | Type: {pick.picking_type_id.name}")

    print("\n--- Existing Invoices ---")
    for inv in order.invoice_ids:
        print(f"Invoice: {inv.name or 'Draft'} | State: {inv.state} | Payment State: {inv.payment_state} | Total: {inv.amount_total:g}")

    print("\n--- Recent Chatter (last 10) ---")
    messages = env['mail.message'].sudo().search([
        ('model', '=', 'sale.order'),
        ('res_id', '=', order.id)
    ], limit=10, order='id desc')
    for m in messages:
        author = m.author_id.name or m.email_from
        body = (m.body or "")[:200].replace('\n', ' ')
        print(f"  - {m.date} [{author}]: {body}")

print("\nDone.")
