# -*- coding: utf-8 -*-
"""Strict rename for the remaining lots to free them up."""
sns_to_fix = ['PC1ACZP1', 'PC1ACZJK', 'PC1ACZNH']
suffix = '-OLD'

print(f"=== STRICT Renaming SNs to {suffix} ===")

for sn_name in sns_to_fix:
    # Use exact match search
    lots = env['stock.lot'].sudo().search([('name', '=', sn_name)])
    
    if not lots:
        print(f"SN: {sn_name} - No lot found to rename.")
        continue

    for lot in lots:
        old_name = lot.name
        new_name = old_name + suffix
        print(f"Lot ID {lot.id}: '{old_name}' -> '{new_name}'")
        
        # Rename
        lot.name = new_name
        print(f"  Success.")

print("\nCOMMITTING CHANGES...")
env.cr.commit()
print("Done.")
