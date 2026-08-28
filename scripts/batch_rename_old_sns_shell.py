# -*- coding: utf-8 -*-
"""Rename multiple SNs to -OLD to free up original names."""
sns_to_fix = ['PC1FSFVX', 'PC1ACZP1', 'PC1ACZJK', 'PC1ACZNH', 'PC1ADA7Q']
suffix = '-OLD'

print(f"=== Batch Renaming SNs to {suffix} ===")

for sn_name in sns_to_fix:
    # Find all lots with this exact name (in case of duplicates, though rare)
    lots = env['stock.lot'].sudo().search([('name', '=', sn_name)])
    
    if not lots:
        print(f"\nSN: {sn_name} - No existing lot found with this exact name.")
        # Check if already renamed
        already_fixed = env['stock.lot'].sudo().search([('name', '=', sn_name + suffix)])
        if already_fixed:
             print(f"  (Note: It seems {sn_name} was already renamed to {sn_name + suffix})")
        continue

    for lot in lots:
        old_name = lot.name
        new_name = old_name + suffix
        
        print(f"\nLot ID {lot.id}: '{old_name}' -> '{new_name}'")
        print(f"  Product: {lot.product_id.display_name}")
        
        # Trace where it is
        quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
        for q in quants:
            print(f"  - Currently at: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
            if q.quantity == 0 and q.reserved_quantity != 0:
                print(f"    -> Clearing ghost reservation of {q.reserved_quantity:g}")
                q.reserved_quantity = 0
        
        # Check recent pickings
        mls = env['stock.move.line'].sudo().search([('lot_id', '=', lot.id)], limit=3, order='date desc')
        for ml in mls:
            print(f"  - Last Movement: {ml.date} | Picking: {ml.picking_id.name} | State: {ml.state}")

        # Rename
        lot.name = new_name
        print(f"  Successfully renamed to {new_name}")

print("\nCommitting changes to database...")
env.cr.commit()
print("Done.")
