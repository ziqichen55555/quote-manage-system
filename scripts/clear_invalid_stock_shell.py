# -*- coding: utf-8 -*-
"""Clear On Hand quantity for all -OLD and _INVALID lots in WH/Stock."""
sns_to_clear = [
    'PC1ACZKQ_INVALID', 'PC1ACMYJ_INVALID', 
    'PC1ACZP1-OLD', 'PC1ACZJK-OLD', 'PC1ACZNH-OLD', 'PC1ADA7Q-OLD', 'PC1FSFVX-OLD'
]

print("=== Clearing Invalid Stock Records ===")

internal_locs = env['stock.location'].sudo().search([('usage', '=', 'internal')])

for sn_name in sns_to_clear:
    lot = env['stock.lot'].sudo().search([('name', '=', sn_name)], limit=1)
    if not lot:
        print(f"\nSN: {sn_name} - Not found, skipping.")
        continue
    
    quants = env['stock.quant'].sudo().search([
        ('lot_id', '=', lot.id),
        ('location_id', 'child_of', internal_locs.ids)
    ])
    
    if not quants:
        print(f"\nSN: {sn_name} - No stock found in internal locations.")
        continue

    print(f"\nProcessing SN: {lot.name} (ID: {lot.id})")
    for q in quants:
        print(f"  - Current: Loc='{q.location_id.display_name}', Qty={q.quantity:g}, Reserved={q.reserved_quantity:g}")
        
        # Reset both quantity and reservation to 0
        q.quantity = 0
        q.reserved_quantity = 0
        print(f"    -> Reset to 0.")

print("\nCommitting changes to database...")
env.cr.commit()
print("Done.")
