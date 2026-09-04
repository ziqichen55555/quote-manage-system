# -*- coding: utf-8 -*-
"""DRY RUN: Rename SN PC1EYJWS to PC1EYJWS-OLD for S00097 / WH/OUT/00082."""

SERIAL_OLD = "PC1EYJWS"
SERIAL_NEW = "PC1EYJWS-OLD"
PICKING_NAME = "WH/OUT/00082"
ORDER_NAME = "S00097"

print(f"=== [DRY RUN] Renaming SN {SERIAL_OLD} to {SERIAL_NEW} ===")

# 1. Verify Picking and Serial
picking = env['stock.picking'].sudo().search([('name', '=', PICKING_NAME)], limit=1)
if not picking:
    print(f"Picking {PICKING_NAME} not found!")
else:
    print(f"Found Picking: {picking.name}, State: {picking.state}, Order: {picking.origin}")
    # Find the move line with this serial
    move_lines = env['stock.move.line'].sudo().search([
        ('picking_id', '=', picking.id)
    ])
    found = False
    for ml in move_lines:
        if ml.lot_id.name == SERIAL_OLD:
            print(f"Verified: Serial {SERIAL_OLD} found in move line for {PICKING_NAME}.")
            found = True
        else:
            print(f"  (Other serial in picking: {ml.lot_id.name})")
    if not found:
        print(f"Warning: Serial {SERIAL_OLD} NOT found in move lines for {PICKING_NAME}.")

# 2. Find Lot
lot = env['stock.lot'].sudo().search([('name', '=', SERIAL_OLD)], limit=1)
if not lot:
    already_fixed = env['stock.lot'].sudo().search([('name', '=', SERIAL_NEW)], limit=1)
    if already_fixed:
        print(f"Result: Serial {SERIAL_OLD} already renamed to {SERIAL_NEW}.")
    else:
        print(f"Result: Serial {SERIAL_OLD} not found in the system!")
else:
    print(f"Lot ID {lot.id}: '{lot.name}' -> '{SERIAL_NEW}'")
    
    # Check for ghost reservations
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        print(f"  - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
        if q.quantity == 0 and q.reserved_quantity != 0:
            print(f"    -> Would clear ghost reservation of {q.reserved_quantity:g}")

print("\n[DRY RUN] No changes committed.")
