# -*- coding: utf-8 -*-
"""Investigate why -OLD and _INVALID lots are in WH/Stock with Qty 1."""
sns_to_check = [
    'PC1ACZKQ_INVALID', 'PC1ACMYJ_INVALID', 
    'PC1ACZP1-OLD', 'PC1ACZJK-OLD', 'PC1ACZNH-OLD', 'PC1ADA7Q-OLD', 'PC1FSFVX-OLD'
]

print("=== Investigating Ghost Stock for Renamed Lots ===")

for sn_name in sns_to_check:
    lot = env['stock.lot'].sudo().search([('name', '=', sn_name)], limit=1)
    if not lot:
        print(f"\nSN: {sn_name} - Not found.")
        continue
    
    print(f"\nLot: {lot.name} (ID: {lot.id})")
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        print(f"  - Quant ID {q.id}: Loc='{q.location_id.display_name}', Qty={q.quantity:g}, Reserved={q.reserved_quantity:g}")
    
    # Check move history to see how it got into WH/Stock
    moves = env['stock.move.line'].sudo().search([('lot_id', '=', lot.id)], order='date desc', limit=5)
    print("  Recent History:")
    for ml in moves:
        print(f"    - {ml.date}: {ml.location_id.display_name} -> {ml.location_dest_id.display_name} | Qty: {ml.quantity:g} | State: {ml.state} | Ref: {ml.reference}")

print("\n=== Checking for Re-created Original SNs ===")
originals = [sn.replace('-OLD', '').replace('_INVALID', '') for sn in sns_to_check]
for orig in set(originals):
    lot = env['stock.lot'].sudo().search([('name', '=', orig)], limit=1)
    if lot:
        print(f"  - Original SN '{orig}' ALREADY EXISTS (ID: {lot.id})")
        quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
        for q in quants:
            print(f"    - Loc='{q.location_id.display_name}', Qty={q.quantity:g}")
    else:
        print(f"  - Original SN '{orig}' is FREE.")

print("\nDone.")
