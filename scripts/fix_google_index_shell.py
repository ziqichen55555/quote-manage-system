# -*- coding: utf-8 -*-
"""Fix Odoo flags that emit homepage noindex (website_indexed, domain, web.base.url)."""
DRY_RUN = True

Page = env["website.page"].sudo().with_context(active_test=False)
ICP = env["ir.config_parameter"].sudo()

home = Page.search([("url", "=", "/")], limit=1)
print("=== FIX GOOGLE INDEX (quote_manage_ui) ===")
print(f"DRY_RUN={DRY_RUN}")
print(f"web.base.url={ICP.get_param('web.base.url')!r}")
if home:
    print(
        f"homepage id={home.id} website_indexed={home.website_indexed} "
        f"is_published={home.is_published} name={home.name!r}"
    )
else:
    print("homepage website.page for url=/ NOT FOUND")

blocked = Page.search([
    ("is_published", "=", True),
    ("website_indexed", "=", False),
    ("url", "!=", "/cookie-policy"),
])
print(f"published pages with website_indexed=False (excl cookie-policy): {len(blocked)}")
for p in blocked[:15]:
    print(f"  id={p.id} url={p.url!r}")

if DRY_RUN:
    print("DRY_RUN: no writes. Set DRY_RUN=False and confirm_apply=APPLY to fix.")
else:
    env["website.page"]._quote_manage_ui_ensure_google_indexable()
    home = Page.search([("url", "=", "/")], limit=1)
    if home:
        print(f"after: homepage website_indexed={home.website_indexed}")
    blocked_after = Page.search_count([
        ("is_published", "=", True),
        ("website_indexed", "=", False),
        ("url", "!=", "/cookie-policy"),
    ])
    print(f"after: blocked pages count={blocked_after}")
print("Done.")
