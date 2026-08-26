# -*- coding: utf-8 -*-
"""Investigate why a product with stock is not visible on the website."""
product_name = "[20WNA07YAU-BT70-CMOSP] ThinkPad T14s Gen 2i"

print(f"=== Investigating Website Visibility for: {product_name} ===")

# Search for the product variant
product = env['product.product'].sudo().search([('display_name', 'ilike', product_name)], limit=1)

if not product:
    # Try searching by name if display_name fails due to formatting
    product = env['product.product'].sudo().search([('name', 'ilike', 'T14s Gen 2i'), ('default_code', 'ilike', '20WNA07YAU')], limit=1)

if not product:
    print("Product not found!")
else:
    template = product.product_tmpl_id
    print(f"Product ID: {product.id}, Template ID: {template.id}")
    print(f"Name: {template.name}")
    print(f"Default Code: {product.default_code}")
    
    # Check key visibility fields
    print("\n--- Visibility Flags ---")
    print(f"Can be Sold (sale_ok): {template.sale_ok}")
    print(f"Is Published (is_published): {template.is_published}")
    print(f"Website ID: {template.website_id.name if template.website_id else 'All Websites'}")
    
    # Check Stock
    print("\n--- Inventory Status ---")
    print(f"Quantity On Hand: {product.qty_available:g}")
    print(f"Forecasted Quantity: {product.virtual_available:g}")
    print(f"Free to Use Quantity: {product.free_qty:g}")
    
    # Check eCommerce / Website settings (Odoo 17 fields)
    print("\n--- eCommerce Settings ---")
    if hasattr(template, 'website_published'):
        print(f"Website Published: {template.website_published}")
    
    # Check if there are any active website-specific variants that might be hidden
    variants = template.product_variant_ids
    print(f"\nTotal Variants: {len(variants)}")
    for v in variants:
        print(f"  - Variant ID {v.id}: {v.display_name}, Active: {v.active}, Qty: {v.qty_available:g}")

print("\nDone.")
