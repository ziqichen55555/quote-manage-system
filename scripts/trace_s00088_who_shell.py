# -*- coding: utf-8 -*-
"""Final surgical audit: who input these SNs?"""
sns = ['PC1FVNDB', 'PC1FVGHZ', 'PC1ACMY6', 'PC1ACMYJ', 'PC1ACZJK', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACZNH']

print(f"=== SN Input Source Audit (S00088) ===")

for sn in sns:
    lot = env['stock.lot'].sudo().search([('name', '=', sn)], limit=1)
    if not lot:
        print(f"\nSN: {sn} - Lot not found!")
        continue
    
    print(f"\nAudit for SN: {sn} (Lot ID: {lot.id})")
    print(f"  Lot Created By: {lot.create_uid.login} at {lot.create_date}")
    
    # Find move lines for this lot in S00088's picking
    order = env['sale.order'].sudo().search([('name', '=', 'S00088')], limit=1)
    if order:
        mls = env['stock.move.line'].sudo().search([
            ('lot_id', '=', lot.id),
            ('picking_id', 'in', order.picking_ids.ids)
        ])
        for ml in mls:
            print(f"  Move Line ID: {ml.id}, Picking: {ml.picking_id.name}, State: {ml.state}")
            print(f"    Created By: {ml.create_uid.login} at {ml.create_date}")
            print(f"    Modified By: {ml.write_uid.login} at {ml.write_date}")

# Check if there are any SIMILAR SNs that might be the "wrong" ones
print("\nChecking for similar SNs (wildcard search):")
# Just a broad check for any lot created around the same time or with similar prefix
similar_lots = env['stock.lot'].sudo().search([('name', '=like', 'PC1%')], limit=20, order='create_date desc')
for slot in similar_lots:
    if slot.name not in sns:
        print(f"  Found potential other lot: {slot.name}, Created By: {slot.create_uid.login} at {slot.create_date}")

print("\nDone.")
