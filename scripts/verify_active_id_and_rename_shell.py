# -*- coding: utf-8 -*-
"""Check active_id 831 and clarify what was modified."""
active_id = 831

print(f"=== Checking ID: {active_id} ===")

# Check if it's a product
product = env['product.product'].sudo().browse(active_id)
if product.exists():
    print(f"ID {active_id} is a PRODUCT: {product.display_name}")
    print(f"  On Hand: {product.qty_available:g}, Reserved: {product.outgoing_qty:g}")
else:
    # Check if it's a template
    template = env['product.template'].sudo().browse(active_id)
    if template.exists():
        print(f"ID {active_id} is a PRODUCT TEMPLATE: {template.name}")
    else:
        # Check if it's a quant (though unlikely as active_id)
        quant = env['stock.quant'].sudo().browse(active_id)
        if quant.exists():
            print(f"ID {active_id} is a QUANT record.")

print("\n=== Verifying the last renamed Lots ===")
sns_to_check = ['PC1FSFVX-OLD', 'PC1ACZP1-OLD', 'PC1ACZJK-OLD', 'PC1ACZNH-OLD', 'PC1ADA7Q-OLD']
for sn in sns_to_check:
    lot = env['stock.lot'].sudo().search([('name', '=', sn)], limit=1)
    if lot:
        print(f"Lot '{lot.name}' exists. ID: {lot.id}, Product: {lot.product_id.display_name}")
    else:
        # Check if original name still exists
        original = sn.replace('-OLD', '')
        lot_orig = env['stock.lot'].sudo().search([('name', '=', original)], limit=1)
        if lot_orig:
            print(f"Lot '{original}' STILL EXISTS (Not renamed?). ID: {lot_orig.id}")
        else:
            print(f"Neither '{sn}' nor '{original}' found.")

print("\nDone.")
