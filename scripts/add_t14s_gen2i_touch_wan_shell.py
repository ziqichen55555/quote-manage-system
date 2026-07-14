# -*- coding: utf-8 -*-
"""Add Touchscreen + WAN filter attributes to ThinkPad T14s Gen 2i shop SKUs.

Targets only the two active CMOSP listings:
  * 20WN0025AU-BT70-CMOSP
  * 20WNA07YAU-BT70-CMOSP

Shop pattern (match T14s Gen 1):
  * Do NOT change product name (keep \"ThinkPad T14s Gen 2i\")
  * Only upsert Touchscreen=Yes and WAN=Enabled attribute lines
  * Do NOT call full _sync_template_attributes (avoids wiping CPU/RAM/Storage)

Default DRY_RUN=True. Set False + workflow confirm_apply=APPLY to write.
"""
DRY_RUN = True  # set False to commit on production

SHOP_SKUS = (
    "20WN0025AU-BT70-CMOSP",
    "20WNA07YAU-BT70-CMOSP",
)

PT = env["product.template"].sudo().with_context(active_test=False)
Line = env["product.template.attribute.line"].sudo()
Pav = env["product.attribute.value"].sudo()


def current_specs(tmpl):
    out = {}
    for line in tmpl.attribute_line_ids:
        if line.value_ids:
            out[line.attribute_id.name] = line.value_ids[0].name
    return out


def upsert_attr(tmpl, attr_xmlid, value_name):
    attr = env.ref(attr_xmlid)
    val = Pav.search(
        [("attribute_id", "=", attr.id), ("name", "=ilike", value_name)],
        limit=1,
    )
    if not val:
        val = Pav.create({"attribute_id": attr.id, "name": value_name[:128]})
    line = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.id == attr.id)
    if line:
        if set(line.value_ids.ids) != {val.id}:
            line.write({"value_ids": [(6, 0, [val.id])]})
            return "updated"
        return "unchanged"
    Line.create(
        {
            "product_tmpl_id": tmpl.id,
            "attribute_id": attr.id,
            "value_ids": [(6, 0, [val.id])],
        }
    )
    return "created"


print("=" * 72)
print("Add Touch + WAN attrs only (no title change)")
print("  SKUs:", ", ".join(SHOP_SKUS))
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

plans = []
for code in SHOP_SKUS:
    tmpl = PT.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        raise SystemExit("Missing shop SKU: %s" % code)
    before = current_specs(tmpl)
    need = before.get("Touchscreen") != "Yes" or before.get("WAN") != "Enabled"
    plans.append({"tmpl": tmpl, "code": code, "before": before, "changed": need})

to_apply = [p for p in plans if p["changed"]]
print("\nFound %d, need update %d, already OK %d" % (
    len(plans), len(to_apply), len(plans) - len(to_apply)
))

for p in plans:
    tmpl = p["tmpl"]
    print("\n--- id=%s code=%r name=%r on_hand=%s" % (
        tmpl.id, p["code"], tmpl.name, tmpl.qty_available
    ))
    print("  before: touch=%r wan=%r cpu=%r" % (
        p["before"].get("Touchscreen"),
        p["before"].get("WAN"),
        p["before"].get("CPU"),
    ))
    if p["changed"]:
        print("  -> upsert Touchscreen=Yes, WAN=Enabled (name untouched)")
    else:
        print("  -> skip")

if not to_apply:
    print("\nNothing to do.")
elif DRY_RUN:
    print("\nDRY_RUN: no changes written. Set DRY_RUN=False and re-run to apply.")
else:
    updated = 0
    for p in to_apply:
        tmpl = p["tmpl"]
        r1 = upsert_attr(tmpl, "quote_manage_ui.attr_touchscreen", "Yes")
        r2 = upsert_attr(tmpl, "quote_manage_ui.attr_wan", "Enabled")
        updated += 1
        print("  %s: touch=%s wan=%s name=%r" % (p["code"], r1, r2, tmpl.name))
    env.cr.commit()
    print("\nCommitted %d template update(s)." % updated)

print("\nDone.")
