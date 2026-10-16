# -*- coding: utf-8 -*-
"""Read-only: trace frontend 500 on /shop, /web/login, /appointment."""
import traceback

print("=== FRONTEND 500 DIAGNOSE (read-only) ===")

mod = env["ir.module.module"].sudo().search([("name", "=", "quote_manage_ui")], limit=1)
print(f"quote_manage_ui installed_version={mod.installed_version!r} state={mod.state!r}")

# Schema: new sale.order flags from guest-checkout work
cr = env.cr
cr.execute(
    """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'sale_order'
      AND column_name LIKE 'rw_website%%'
    ORDER BY 1
    """
)
cols = [r[0] for r in cr.fetchall()]
print(f"sale_order rw_website* columns: {cols}")
expected = {"rw_website_quotation_staff_notified", "rw_website_sale_staff_notified"}
missing = expected - set(cols)
if missing:
    print(f"MISSING COLUMNS (likely 500 on cart/shop): {sorted(missing)}")

# Broken QWeb views block many routes
View = env["ir.ui.view"].sudo()
xmlids = [
    "web.login",
    "website_sale.products",
    "auth_signup.login",
    "auth_signup.signup",
    "quote_manage_ui.reware_login",
    "quote_manage_ui.reware_signup",
    "quote_manage_ui.reware_address_guest_intro",
]
print("\n--- QWeb render smoke test ---")
for xid in xmlids:
    try:
        env.ref(xid)
    except Exception as e:
        print(f"{xid}: MISSING REF {e!r}")
        continue
    try:
        env["ir.ui.view"]._render_template(xid, {})
        print(f"{xid}: render OK")
    except Exception as e:
        print(f"{xid}: RENDER FAIL {type(e).__name__}: {e}")
        traceback.print_exc()

# Controller path used by /shop listing
print("\n--- WebsiteSale extra shop values ---")
try:
    from odoo.addons.quote_manage_ui.controllers.website_sale import WebsiteSale

    ctrl = WebsiteSale()
    base = {
        "search_product": env["product.template"].sudo().search(
            [("website_published", "=", True), ("sale_ok", "=", True)], limit=5
        ),
        "attrib_set": set(),
        "category": env["product.public.category"],
    }
    ctrl._get_additional_shop_values(dict(base))
    ctrl._get_additional_extra_shop_values(dict(base))
    print("WebsiteSale shop helpers: OK")
except Exception as e:
    print(f"WebsiteSale helpers FAIL {type(e).__name__}: {e}")
    traceback.print_exc()

# External HTTP from container (confirms prod still 500)
print("\n--- HTTP probe from server ---")
try:
    import urllib.error
    import urllib.request

    for path in ("/shop", "/web/login", "/contactus", "/"):
        url = f"https://www.reware-project.com{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                print(f"{path}: {resp.status}")
        except urllib.error.HTTPError as he:
            print(f"{path}: HTTP {he.code}")
        except Exception as e:
            print(f"{path}: {type(e).__name__}: {e}")
except Exception as e:
    print(f"HTTP probe skipped: {e}")

print("Done.")
