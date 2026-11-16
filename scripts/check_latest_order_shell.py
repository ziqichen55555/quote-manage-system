# -*- coding: utf-8 -*-
"""Check latest website order state."""
import datetime

one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
orders = env['sale.order'].sudo().search([
    ('website_id', '!=', False),
    ('create_date', '>', one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'))
], order='id desc', limit=1)

if not orders:
    print("No recent website orders found.")
else:
    order = orders[0]
    print(f"Order: {order.name}, State: {order.state}, Total: {order.amount_total}")
    print(f"Carrier: {order.carrier_id.name if order.carrier_id else 'None'}")
    print(f"Amount Delivery: {order.amount_delivery}")
    print(f"Postcode: {order.partner_shipping_id.zip}")
    print("Lines:")
    for line in order.order_line:
        print(f"- {line.product_id.display_name}: Qty {line.product_uom_qty}, Price {line.price_unit}, Is Delivery {line.is_delivery}")
