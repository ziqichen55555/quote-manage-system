# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def run(env):
    order_name = 'S00117' # Assuming Odoo standard naming
    order = env['sale.order'].search([('name', 'ilike', '117')], limit=1)
    
    if not order:
        print(f"Order matching '117' not found.")
        return

    print(f"Order: {order.name} (ID: {order.id})")
    print(f"State: {order.state}")
    print(f"Invoice Status: {order.invoice_status}")
    print(f"Partner: {order.partner_id.name}")
    print("-" * 40)
    
    for line in order.order_line:
        print(f"Product: {line.product_id.display_name}")
        print(f"  Quantity Ordered: {line.product_uom_qty}")
        print(f"  Quantity Delivered: {line.qty_delivered}")
        print(f"  Quantity Invoiced: {line.qty_invoiced}")
        print(f"  Invoice Status: {line.invoice_status}")
        print(f"  Policy: {line.product_id.invoice_policy}")
        if line.product_id.type == 'service':
            print(f"  Service Tracking: {line.product_id.service_tracking}")
            print(f"  Upsell Threshold: {line.product_id.service_upsell_threshold}")
        print("-" * 20)

if __name__ == "__main__":
    # This is intended to be run via odoo shell or a similar wrapper
    pass
