# -*- coding: utf-8 -*-
"""Rename incorrectly delivered SNs to free them up."""
sns_to_fix = ['PC1ACMYJ', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACMY6']
suffix = "_INVALID"
DRY_RUN = True  # Initial preview

print(f"=== {'[DRY RUN] ' if DRY_RUN else ''}Fixing Incorrect SNs ===")

for sn_name in sns_to_fix:
    lot = env['stock.lot'].sudo().search([('name', '=', sn_name)], limit=1)
    if not lot:
        print(f"SN {sn_name}: Not found, skipping.")
        continue
    
    old_name = lot.name
    new_name = old_name + suffix
    
    print(f"Lot ID {lot.id}: '{old_name}' -> '{new_name}'")
    
    # Check current position
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        print(f"  - Currently at: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

    if not DRY_RUN:
        lot.name = new_name
        print(f"  Successfully renamed to {new_name}")

if DRY_RUN:
    print("\n*** This was a DRY RUN. No changes were made to the database. ***")

print("\nDone.")
