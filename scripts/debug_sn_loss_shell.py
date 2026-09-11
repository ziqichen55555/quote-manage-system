# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

# active_test=False is CRITICAL to see archived data
Product = env['product.template'].with_context(active_test=False)
Lot = env['stock.lot'].with_context(active_test=False)

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

print("--- Product Status Summary ---")
all_products = Product.search([])
print(f"Total Products: {len(all_products)}")
print(f"Active Products: {len(all_products.filtered(lambda p: p.active))}")
print(f"Archived Products: {len(all_products.filtered(lambda p: not p.active))}")

print("\n--- Serial Numbers (stock.lot) Summary ---")
all_lots = Lot.search([])
print(f"Total SNs (Lots): {len(all_lots)}")

# Check lots created today
lots_today = Lot.search([('create_date', '>=', today)])
print(f"SNs created today: {len(lots_today)}")

# Check specific SNs user mentioned
# Note: The user mentioned names and SNs like [20T0003UAU-...]
# These look like internal references or SNs. 
mentioned_refs = ['20T0003UAU', '20WNS6LL00', '20WNS1M500', '20WNA07YAU', '20WN0025AU', '20L8SDCE00', '20L8SBL100', '20NYS4CP00']

print("\n--- Checking Mentioned Refs in Lots & Products ---")
for ref in mentioned_refs:
    # Search in Lots
    found_lots = Lot.search(['|', ('name', 'ilike', ref), ('ref', 'ilike', ref)])
    # Search in Product Internal Reference
    found_products = Product.search([('default_code', 'ilike', ref)])
    
    lot_info = f"{len(found_lots)} lots" if found_lots else "0 lots"
    prod_info = f"{len(found_products)} products" if found_products else "0 products"
    print(f"Ref '{ref}': Found {lot_info}, {prod_info}")
    
    if found_products:
        for p in found_products:
            print(f"  -> Product ID: {p.id} | Name: {p.name} | Active: {p.active} | Ref: {p.default_code}")

print("\n--- Batch Analysis (What happened around 04:57-04:58) ---")
# Find products archived around that time
archived_batch = Product.search([
    ('active', '=', False),
    ('write_date', '>=', today + timedelta(hours=4, minutes=50)),
    ('write_date', '<=', today + timedelta(hours=5, minutes=5))
])
print(f"Products archived/modified in import window (04:50-05:05): {len(archived_batch)}")
for p in archived_batch[:10]:
    print(f"  Archived Batch ID: {p.id} | Name: {p.name} | Ref: {p.default_code}")
