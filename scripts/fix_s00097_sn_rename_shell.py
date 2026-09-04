# -*- coding: utf-8 -*-
"""Rename SN PC1EYJWS to PC1EYJWS-OLD for S00097 / WH/OUT/00082."""

SERIAL_OLD = "PC1EYJWS"
SERIAL_NEW = "PC1EYJWS-OLD"
PICKING_NAME = "WH/OUT/00082"
ORDER_NAME = "S00097"

print(f"=== Renaming SN {SERIAL_OLD} to {SERIAL_NEW} ===")

# 1. Verify Picking and Serial
picking = env['stock.picking'].sudo().search([('name', '=', PICKING_NAME)], limit=1)
if not picking:
    print(f"Picking {PICKING_NAME} not found!")
else:
    print(f"Found Picking: {picking.name}, State: {picking.state}, Order: {picking.origin}")
    # Find the move line with this serial
    move_line = env['stock.move.line'].sudo().search([
        ('picking_id', '=', picking.id),
        ('lot_id.name', '=', SERIAL_OLD)
    ], limit=1)
    if move_line:
        print(f"Verified: Serial {SERIAL_OLD} found in move line for {PICKING_NAME}.")
    else:
        print(f"Warning: Serial {SERIAL_OLD} NOT found in move lines for {PICKING_NAME}.")

# 2. Find and Rename Lot
lot = env['stock.lot'].sudo().search([('name', '=', SERIAL_OLD)], limit=1)
if not lot:
    already_fixed = env['stock.lot'].sudo().search([('name', '=', SERIAL_NEW)], limit=1)
    if already_fixed:
        print(f"Serial {SERIAL_OLD} already renamed to {SERIAL_NEW}.")
    else:
        print(f"Serial {SERIAL_OLD} not found in the system!")
else:
    print(f"Lot ID {lot.id}: '{lot.name}' -> '{SERIAL_NEW}'")
    
    # Check for ghost reservations (consistent with other fix scripts)
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        if q.quantity == 0 and q.reserved_quantity != 0:
            print(f"  -> Clearing ghost reservation of {q.reserved_quantity:g} in {q.location_id.display_name}")
            q.sudo().write({'reserved_quantity': 0})
            
    lot.sudo().write({'name': SERIAL_NEW})
    print(f"Successfully renamed to {SERIAL_NEW}")

print("\nCommitting changes...")
env.cr.commit()
print("Done.")
