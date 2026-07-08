# -*- coding: utf-8 -*-
"""Audit website-visible refurb stock on production."""
cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
PT = env["product.template"].sudo().with_context(active_test=False)

dom = [
    ("type", "=", "product"),
    ("tracking", "=", "serial"),
    ("public_categ_ids", "in", [cat_l, cat_d]),
]

published = []
active_stock = []
for tmpl in PT.search(dom, order="default_code"):
    code = (tmpl.default_code or "").strip()
    try:
        wqty = float(tmpl._rw_website_available_qty() or 0)
    except Exception:
        wqty = 0.0
    oh = float(tmpl.qty_available or 0)
    if tmpl.is_published and wqty > 0:
        published.append((code, tmpl.id, wqty, oh, tmpl.active))
    if tmpl.active and oh > 0:
        active_stock.append((code, tmpl.id, wqty, oh, tmpl.is_published))

print("=" * 72)
print("WEBSITE STOCK AUDIT")
print("=" * 72)
print(f"Published refurb with website_qty > 0: {len(published)}")
print(f"Total website units: {sum(x[2] for x in published):.0f}")
print(f"Active refurb with on_hand > 0: {len(active_stock)}")
print(f"Total on_hand units: {sum(x[3] for x in active_stock):.0f}")
print()

print("--- Published on website (website_qty > 0) ---")
for code, tid, wqty, oh, active in sorted(published, key=lambda x: -x[2])[:40]:
    print(f"  {code or '(no code)'} tmpl={tid} website_qty={wqty:.0f} on_hand={oh:.0f} active={active}")
if len(published) > 40:
    print(f"  ... +{len(published) - 40} more SKUs")

print()
print("--- Active with WH stock but NOT published ---")
unpub = [x for x in active_stock if not x[4] and x[3] > 0]
for code, tid, wqty, oh, _ in sorted(unpub, key=lambda x: -x[3])[:15]:
    print(f"  {code or '(no code)'} tmpl={tid} on_hand={oh:.0f} website_qty={wqty:.0f}")
print(f"  count={len(unpub)}")
print("Done.")
