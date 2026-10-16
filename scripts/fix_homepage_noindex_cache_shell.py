# -*- coding: utf-8 -*-
"""Bust stale homepage qweb t-cache (robots noindex) on live web workers via page/view touch."""
DRY_RUN = False

Page = env["website.page"].sudo().with_context(active_test=False)
home = Page.search([("url", "=", "/")], limit=1)
print("=== HOMEPAGE NOINDEX CACHE BUST ===")
print(f"DRY_RUN={DRY_RUN}")
if not home:
    print("No website.page for /")
else:
    print(
        f"before id={home.id} website_indexed={home.website_indexed} "
        f"meta_title={(home.website_meta_title or '')[:60]!r}"
    )

if DRY_RUN:
    print("DRY_RUN: no writes.")
else:
    if home:
        title = (home.website_meta_title or "").strip() or (
            "Re-Ware Project | Official reware-project.com - Perth WA"
        )
        home.write({"website_indexed": False})
        home.write({
            "website_indexed": True,
            "website_meta_title": title,
        })
        view = home.view_id.sudo()
        if view:
            view.write({"name": view.name})
        print(f"after website_indexed={home.website_indexed}")
    env.registry.clear_cache()
    print("Done. If / still shows noindex, restart web: Repair production workflow.")
