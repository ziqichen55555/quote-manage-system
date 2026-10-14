# -*- coding: utf-8 -*-
"""Read-only: report Odoo settings that affect Google indexing (production Odoo shell)."""
Website = env["website"].sudo()
Page = env["website.page"].sudo().with_context(active_test=False)
PT = env["product.template"].sudo().with_context(active_test=False)
ICP = env["ir.config_parameter"].sudo()

print("=== GOOGLE INDEX AUDIT (read-only) ===")
print(f"web.base.url={ICP.get_param('web.base.url')}")
for site in Website.search([]):
    print(f"website id={site.id} domain={site.domain!r}")

not_indexed = Page.search([
    ("is_published", "=", True),
    ("website_indexed", "=", False),
])
print(f"Published pages with website_indexed=False: {len(not_indexed)}")
for p in not_indexed[:25]:
    print(f"  url={p.url!r} name={p.name!r}")

published_products = PT.search_count([("website_published", "=", True)])
missing_seo = PT.search_count([
    ("website_published", "=", True),
    "|",
    ("website_meta_description", "=", False),
    ("website_meta_description", "=", ""),
])
print(f"Published products: {published_products}")
print(f"Published products without custom meta description: {missing_seo}")
print()
print("If pages show not indexed, deploy quote_manage_ui 1.0.180+ or run")
print("env['website.page']._quote_manage_ui_ensure_google_indexable() once.")
print("Then use Google Search Console: submit sitemap.xml and request indexing.")
print("Done.")
