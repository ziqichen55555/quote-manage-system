# -*- coding: utf-8 -*-
"""Fix homepage noindex: index flags, domain, and stale Odoo t-cache on website.page."""
DRY_RUN = False

Page = env["website.page"].sudo().with_context(active_test=False)
Website = env["website"].sudo()
ICP = env["ir.config_parameter"].sudo()

home = Page.search([("url", "=", "/")], limit=1)
print("=== FIX GOOGLE INDEX (quote_manage_ui) ===")
print(f"DRY_RUN={DRY_RUN}")
print(f"web.base.url={ICP.get_param('web.base.url')!r}")
for site in Website.search([]):
    ok = site._is_indexable_url("https://www.reware-project.com/")
    print(f"website id={site.id} domain={site.domain!r} indexable_www={ok}")
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

if DRY_RUN:
    print("DRY_RUN: no writes. Set DRY_RUN=False and confirm_apply=APPLY to fix.")
else:
    env["website.page"]._quote_manage_ui_ensure_google_indexable()
    if home:
        # Rewrite same value to bust ir.qweb t-cache for cached homepage head (robots meta).
        home.write({"website_indexed": True})
    env["website"].browse([w.id for w in Website.search([])])._quote_clear_website_menu_template_cache()
    env.registry.clear_cache()
    home = Page.search([("url", "=", "/")], limit=1)
    if home:
        print(f"after: homepage website_indexed={home.website_indexed}")
    blocked_after = Page.search_count([
        ("is_published", "=", True),
        ("website_indexed", "=", False),
        ("url", "!=", "/cookie-policy"),
    ])
    print(f"after: blocked pages count={blocked_after}")
    print("Caches cleared; fetch https://www.reware-project.com/ to verify robots meta.")
print("Done.")
