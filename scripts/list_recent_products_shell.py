# -*- coding: utf-8 -*-
# List last 50 updated products
products = env['product.template'].with_context(active_test=False).search([], order='write_date desc', limit=60)
for p in products:
    print(f"ID: {p.id} | Name: {p.name} | Active: {p.active} | Updated: {p.write_date}")
