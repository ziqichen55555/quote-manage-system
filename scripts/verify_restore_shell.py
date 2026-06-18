# -*- coding: utf-8 -*-
Template = env["product.template"].sudo()
Product = env["product.product"].sudo()
print("ACTIVE_TEMPLATES:", Template.search_count([("active", "=", True)]))
print("ACTIVE_VARIANTS:", Product.search_count([("active", "=", True)]))
print("PUBLISHED:", Template.search_count([("website_published", "=", True), ("active", "=", True)]))
t14 = Template.search([("name", "ilike", "ThinkPad T14s")])
print("T14s_TEMPLATES:", len(t14))
for t in t14:
    print(f"  id={t.id} variants={len(t.product_variant_ids)} qty={t.qty_available}")
