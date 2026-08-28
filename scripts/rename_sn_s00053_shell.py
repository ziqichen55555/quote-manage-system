# -*- coding: utf-8 -*-
"""Rename SN PC1PQ9M8 to PC1PQ9M8-OLD and free it up."""
sn_to_fix = 'PC1PQ9M8'
suffix = '-OLD'
order_name = 'S00053'

print(f"=== Renaming SN: {sn_to_fix} to {sn_to_fix + suffix} ===")

lot = env['stock.lot'].sudo().search([('name', '=', sn_to_fix)], limit=1)
if not lot:
    print(f"Lot {sn_to_fix} not found, skipping.")
else:
    old_name = lot.name
    new_name = old_name + suffix
    
    print(f"Lot ID {lot.id}: '{old_name}' -> '{new_name}'")
    
    # 1. Rename the lot
    lot.name = new_name
    print(f"  Successfully renamed to {new_name}")

    # 2. Add chatter message to S00053
    order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)
    if order:
        order.message_post(body=f"Serial number {old_name} has been renamed to {new_name} to free up the original name for resale, as it was found to be on hand.")
        print(f"  Added note to {order.name} chatter.")

    # 3. Commit changes
    print("\nCommitting changes...")
    env.cr.commit()
    print("Done.")
