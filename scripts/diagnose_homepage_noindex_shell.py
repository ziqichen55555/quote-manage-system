# -*- coding: utf-8 -*-
"""Read-only: why does / emit robots noindex?"""
Page = env["website.page"].sudo().with_context(active_test=False)
Website = env["website"].sudo()

print("=== HOMEPAGE NOINDEX DIAGNOSE (read-only) ===")
for site in Website.search([]):
    print(
        f"website id={site.id} domain={site.domain!r} "
        f"homepage_url={site.homepage_url!r}"
    )
    for url in (
        "https://www.reware-project.com/",
        "http://www.reware-project.com/",
        "https://reware-project.com/",
    ):
        print(f"  _is_indexable_url({url!r})={site._is_indexable_url(url)}")

pages = Page.search([("url", "=", "/")], order="id")
print(f"website.page count url=/ : {len(pages)}")
for p in pages:
    print(
        f"  id={p.id} website_id={p.website_id.id} indexed={p.website_indexed} "
        f"published={p.is_published} name={p.name!r} view_id={p.view_id.id}"
    )
print("Done.")
