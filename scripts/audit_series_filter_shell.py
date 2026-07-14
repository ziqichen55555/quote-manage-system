# -*- coding: utf-8 -*-
"""Careful Series filter audit (read-only).

Reports:
  * Every Series attribute value + how many templates / published shop templates use it
  * Duplicate / near-duplicate names (case / Gen suffix)
  * Whether orphan Gen-suffixed values still exist with zero product usage
"""
import re
from collections import defaultdict

PT = env["product.template"].sudo().with_context(active_test=False)
PTAL = env["product.template.attribute.line"].sudo()
Pav = env["product.attribute.value"].sudo()
series_attr = env.ref("quote_manage_ui.attr_series")

print("=" * 72)
print("Series attribute audit (read-only)")
print("=" * 72)

vals = Pav.search([("attribute_id", "=", series_attr.id)], order="name, id")
print("\n[1] All Series values (%d):" % len(vals))

rows = []
for v in vals:
    lines = PTAL.search(
        [("attribute_id", "=", series_attr.id), ("value_ids", "in", [v.id])]
    )
    tmpls = lines.mapped("product_tmpl_id")
    pub = tmpls.filtered(
        lambda t: t.website_published and t.sale_ok and t.active
    )
    rows.append(
        {
            "id": v.id,
            "name": v.name,
            "all": len(tmpls),
            "shop": len(pub),
            "shop_codes": pub.mapped("default_code")[:8],
            "inactive_codes": tmpls.filtered(lambda t: not t.active).mapped(
                "default_code"
            )[:5],
        }
    )

for r in sorted(rows, key=lambda x: (-x["shop"], -x["all"], x["name"] or "")):
    flag = []
    if r["shop"] == 0 and r["all"] == 0:
        flag.append("ORPHAN")
    elif r["shop"] == 0 and r["all"] > 0:
        flag.append("NO_SHOP")
    if re.search(r"\bGen\b", r["name"] or "", re.I):
        flag.append("HAS_GEN")
    print(
        "  id=%-4s shop=%-3s all=%-3s %-40s %s"
        % (r["id"], r["shop"], r["all"], repr(r["name"]), " ".join(flag) or "OK")
    )
    if r["shop_codes"]:
        print("           shop SKUs: %s" % ", ".join(c or "?" for c in r["shop_codes"]))
    if r["inactive_codes"] and r["shop"] == 0:
        print(
            "           inactive: %s"
            % ", ".join(c or "?" for c in r["inactive_codes"])
        )

print("\n[2] Near-duplicates (same letters ignoring case / spaces / Gen):")
buckets = defaultdict(list)
for r in rows:
    key = re.sub(r"\s+", "", (r["name"] or "").lower())
    key = re.sub(r"gen\d+\w*", "GEN", key)
    buckets[key].append(r)
found_dup = False
for key, group in sorted(buckets.items()):
    if len(group) < 2:
        continue
    found_dup = True
    print("  group %r:" % key)
    for r in group:
        print("    id=%s name=%r shop=%s all=%s" % (r["id"], r["name"], r["shop"], r["all"]))
if not found_dup:
    print("  (none)")

orphans = [r for r in rows if r["all"] == 0]
gen_orphans = [r for r in orphans if re.search(r"\bGen\b", r["name"] or "", re.I)]
print("\n[3] Summary")
print("  Series values total: %d" % len(rows))
print("  With shop products:  %d" % sum(1 for r in rows if r["shop"] > 0))
print("  Orphans (0 templates): %d" % len(orphans))
print("  Gen-suffixed orphans: %d" % len(gen_orphans))
for r in gen_orphans:
    print("    - id=%s %r" % (r["id"], r["name"]))

print(
    "\n[4] Shop filter recommendation:\n"
    "  Keep only Series values with shop>0.\n"
    "  Safe to delete orphans (all=0). Review NO_SHOP before deleting.\n"
    "  Frontend should use search_product-linked values (+ fix t-cache)."
)
print("\nDone.")
