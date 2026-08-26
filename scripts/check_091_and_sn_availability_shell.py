# -*- coding: utf-8 -*-
"""Check picking WH/OUT/00091 and current availability of ZKQ and MYJ."""
sns = ['PC1ACZKQ', 'PC1ACMYJ']
picking_name = "WH/OUT/00091"

print(f"=== Checking {picking_name} for S00111 ===")
picking = env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

if not picking:
    print(f"Picking {picking_name} not found.")
else:
    print(f"State: {picking.state}")
    for ml in picking.move_line_ids:
        sn = ml.lot_id.name if ml.lot_id else "No SN"
        print(f"  - Move Line: Lot='{sn}', Qty={ml.quantity:g}")

print("\n=== Checking if original SNs exist in system ===")
for sn in sns:
    lot = env['stock.lot'].sudo().search([('name', '=', sn)], limit=1)
    if lot:
        print(f"  - Lot '{sn}' EXISTS (ID: {lot.id}) - Product: {lot.product_id.display_name}")
    else:
        print(f"  - Lot '{sn}' DOES NOT EXIST. (It is free to be created)")

print("\nDone.")
