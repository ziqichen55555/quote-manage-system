# -*- coding: utf-8 -*-
"""Read-only: published shop content missing SEO metadata (production Odoo shell)."""
PT = env["product.template"].sudo().with_context(active_test=False)
Page = env["website.page"].sudo().with_context(active_test=False)

try:
    cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
    cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
    shop_dom = [
        ("type", "=", "product"),
        ("website_published", "=", True),
        ("public_categ_ids", "in", [cat_l, cat_d]),
    ]
except Exception:
    shop_dom = [("type", "=", "product"), ("website_published", "=", True)]

LIMIT = 30

missing_meta = []
placeholder_desc = []
no_image = []

for tmpl in PT.search(shop_dom, order="default_code"):
    code = (tmpl.default_code or "").strip()
    title = (tmpl.website_meta_title or "").strip()
    desc = (tmpl.website_meta_description or "").strip()
    keywords = (tmpl.website_meta_keywords or "").strip()
    if not title or not desc:
        missing_meta.append((code, tmpl.id, bool(title), bool(desc), bool(keywords)))
    if desc.lower() in ("", "this is the homepage of the website"):
        placeholder_desc.append((code, tmpl.id, desc[:80]))
    if not tmpl.image_1920:
        no_image.append((code, tmpl.id))

pages_missing = []
for page in Page.search([("website_published", "=", True)], order="url"):
    title = (page.website_meta_title or "").strip()
    desc = (page.website_meta_description or "").strip()
    if not title or not desc:
        pages_missing.append((page.url or "", page.id, bool(title), bool(desc)))

print("=" * 72)
print("SEO METADATA AUDIT (read-only)")
print("=" * 72)
print(f"Published shop products (scope): {PT.search_count(shop_dom)}")
print(f"Missing title or description: {len(missing_meta)}")
print(f"Placeholder / empty description: {len(placeholder_desc)}")
print(f"Published shop products without main image: {len(no_image)}")
print(f"Published website pages missing title or description: {len(pages_missing)}")
print()

print(f"--- Products missing meta (first {LIMIT}) ---")
for row in missing_meta[:LIMIT]:
    code, tid, has_t, has_d, has_k = row
    print(
        f"  {code or '(no code)'} tmpl={tid} "
        f"title={has_t} desc={has_d} keywords={has_k}"
    )
if len(missing_meta) > LIMIT:
    print(f"  ... +{len(missing_meta) - LIMIT} more")

print()
print(f"--- Pages missing meta (first {LIMIT}) ---")
for url, pid, has_t, has_d in pages_missing[:LIMIT]:
    print(f"  {url or '/'} page={pid} title={has_t} desc={has_d}")
if len(pages_missing) > LIMIT:
    print(f"  ... +{len(pages_missing) - LIMIT} more")

print()
print("Done.")
