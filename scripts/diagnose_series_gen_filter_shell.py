# -*- coding: utf-8 -*-
"""Diagnose why Series sidebar shows Gen-suffixed values (read-only)."""
import re

PT = env["product.template"].sudo().with_context(active_test=False)
series_attr = env.ref("quote_manage_ui.attr_series")
Pav = env["product.attribute.value"].sudo()

print("=== Series attribute values containing 'Gen' ===")
vals = Pav.search([("attribute_id", "=", series_attr.id), ("name", "ilike", "%Gen%")])
for v in vals:
    lines = env["product.template.attribute.line"].sudo().search(
        [("attribute_id", "=", series_attr.id), ("value_ids", "in", [v.id])]
    )
    tmpls = lines.mapped("product_tmpl_id")
    print("\nVALUE id=%s name=%r used_by=%d templates" % (v.id, v.name, len(tmpls)))
    for t in tmpls[:20]:
        print(
            "  code=%r active=%s pub=%s sale_ok=%s name=%r"
            % (t.default_code, t.active, t.website_published, t.sale_ok, t.name)
        )
    if len(tmpls) > 20:
        print("  ... +%d more" % (len(tmpls) - 20))

print("\n=== Sample published shop Series values (top) ===")
from collections import Counter
c = Counter()
for t in PT.search([("website_published", "=", True), ("sale_ok", "=", True)]):
    for line in t.attribute_line_ids:
        if line.attribute_id == series_attr and line.value_ids:
            c[line.value_ids[0].name] += 1
for name, n in c.most_common(40):
    mark = " <<GEN" if re.search(r"\bGen\b", name or "", re.I) else ""
    print("  %4d  %r%s" % (n, name, mark))

print("\nDone.")
