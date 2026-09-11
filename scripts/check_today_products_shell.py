# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

# Find products updated today
today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
products = env['product.template'].search([('write_date', '>=', today_start)], order='write_date desc')

print(f"Total products updated today: {len(products)}")

active_today = products.filtered(lambda p: p.active)
archived_today = products.filtered(lambda p: not p.active)

print(f"Active today: {len(active_today)}")
print(f"Archived today: {len(archived_today)}")

# List the last 100 updated products to see the full picture
for p in products[:100]:
    print(f"ID: {p.id} | Name: {p.name} | Active: {p.active} | Updated: {p.write_date}")
