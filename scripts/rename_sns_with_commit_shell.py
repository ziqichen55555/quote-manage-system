# -*- coding: utf-8 -*-
"""Rename incorrectly delivered SNs with COMMIT."""
sns_to_fix = ['PC1ACMYJ', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACMY6']
suffix = "_INVALID"

print(f"=== Fixing Incorrect SNs (with COMMIT) ===")

for sn_name in sns_to_fix:
    lot = env['stock.lot'].sudo().search([('name', '=', sn_name)], limit=1)
    if not lot:
        # Check if already renamed in a previous run that somehow didn't show up
        already_fixed = env['stock.lot'].sudo().search([('name', '=', sn_name + suffix)], limit=1)
        if already_fixed:
            print(f"SN {sn_name} already renamed to {sn_name + suffix}")
        else:
            print(f"SN {sn_name}: Not found, skipping.")
        continue
    
    old_name = lot.name
    new_name = old_name + suffix
    
    print(f"Lot ID {lot.id}: '{old_name}' -> '{new_name}'")
    
    # Check and clear ghost reservations
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        print(f"  - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
        if q.quantity == 0 and q.reserved_quantity != 0:
            print(f"    -> Clearing ghost reservation of {q.reserved_quantity:g}")
            q.reserved_quantity = 0

    lot.name = new_name
    print(f"  Successfully renamed to {new_name}")

print("\nCommitting changes...")
env.cr.commit()
print("Done.")
