# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

two_hours_ago = datetime.now() - timedelta(hours=2)
products = env['product.template'].with_context(active_test=False).search([('write_date', '>=', two_hours_ago)], order='write_date desc')

print(f"Analyzing {len(products)} products touched in the last 2 hours...")

for p in products:
    state = "ACTIVE" if p.active else "ARCHIVED"
    created_today = "CREATED TODAY" if p.create_date >= two_hours_ago else f"EXISTING (Created: {p.create_date})"
    print(f"ID: {p.id} | Ref: {p.default_code} | Name: {p.name} | Status: {state} | {created_today}")

# Let's specifically look for the SNs the user mentioned if they are in the default_code or description
# The user mentioned SKUs like 20T0003UAU...
 skus = ['20T0003UAU', '20WNS6LL00', '20WNS1M500', '20WNA07YAU', '20WN0025AU', '20L8SDCE00', '20L8SBL100', '20NYS4CP00']
 print("\nChecking specific SKUs mentioned by user:")
 for sku in skus:
     found = env['product.template'].with_context(active_test=False).search([('default_code', 'ilike', sku)])
     if found:
         for f in found:
             print(f"SKU {sku} matched Product ID {f.id} | Name: {f.name} | Active: {f.active}")
     else:
         print(f"SKU {sku} NOT FOUND in default_code")
