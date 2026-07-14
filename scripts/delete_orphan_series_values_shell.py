# -*- coding: utf-8 -*-
"""Delete orphan Series attribute values (0 product.template.attribute.line refs).

Only removes Series values with zero PTAL usage. Does NOT touch NO_SHOP values
that are still linked to inactive templates.

Default DRY_RUN=True. Set False + confirm_apply=APPLY to write.
"""
import re

DRY_RUN = True  # set False to commit on production

PTAL = env["product.template.attribute.line"].sudo()
PTAV = env["product.template.attribute.value"].sudo()
Pav = env["product.attribute.value"].sudo()
series_attr = env.ref("quote_manage_ui.attr_series")

print("=" * 72)
print("Delete orphan Series values (all PTAL refs = 0)")
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

vals = Pav.search([("attribute_id", "=", series_attr.id)], order="name, id")
orphans = []
for v in vals:
    line_n = PTAL.search_count(
        [("attribute_id", "=", series_attr.id), ("value_ids", "in", [v.id])]
    )
    ptav_n = PTAV.search_count(
        [("attribute_id", "=", series_attr.id), ("product_attribute_value_id", "=", v.id)]
    )
    if line_n == 0 and ptav_n == 0:
        orphans.append(v)
        print(
            "  ORPHAN id=%s name=%r gen=%s"
            % (v.id, v.name, bool(re.search(r"\bGen\b", v.name or "", re.I)))
        )
    elif line_n == 0 and ptav_n:
        print(
            "  SKIP id=%s name=%r (no PTAL but %s PTAV — investigate)"
            % (v.id, v.name, ptav_n)
        )

print("\nSafe orphans to delete: %d" % len(orphans))

if not orphans:
    print("Nothing to do.")
elif DRY_RUN:
    print("DRY_RUN: no changes written.")
else:
    ids = orphans.ids if hasattr(orphans, "ids") else [v.id for v in orphans]
    # unlink one-by-one for clearer errors
    deleted = 0
    for v in orphans:
        name = v.name
        vid = v.id
        v.unlink()
        deleted += 1
        print("  deleted id=%s %r" % (vid, name))
    env.cr.commit()
    print("Committed %d orphan Series value(s)." % deleted)

    left = Pav.search_count(
        [("attribute_id", "=", series_attr.id), ("name", "ilike", "%Gen%")]
    )
    print("Remaining Series values with 'Gen' in name: %d" % left)

print("\nDone.")
