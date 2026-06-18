# -*- coding: utf-8 -*-
serial_products = env["product.template"].sudo().search_count([("tracking", "=", "serial")])
no_track_laptops = env["product.template"].sudo().search_count([
    ("tracking", "=", "none"),
    ("categ_id.name", "ilike", "laptop"),
])
total_variants = env["product.product"].sudo().search_count([])
print("SERIAL_TRACKING_TEMPLATES:", serial_products)
print("LAPTOP_NO_TRACKING:", no_track_laptops)
print("TOTAL_VARIANTS:", total_variants)
