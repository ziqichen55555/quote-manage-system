# -*- coding: utf-8 -*-
"""Read-only: multi-line description lines missing sentence capitals."""
import re

Product = env["product.template"].sudo()
SaleOrderLine = env["sale.order.line"].sudo()

SENT_START = re.compile(r"^[A-Z0-9\"(\[]")  # allow SKU brackets / quotes


def plain_lines(text):
    if not text:
        return []
    plain = re.sub(r"<[^>]+>", " ", text or "")
    return [ln.strip() for ln in plain.replace("\r", "\n").split("\n") if ln.strip()]


def bad_lines_in_text(text):
    lines = plain_lines(text)
    bad = []
    for i, ln in enumerate(lines):
        # Skip first line if it looks like [SKU] title — check body lines only
        if i == 0 and ln.startswith("["):
            continue
        if ln and not re.match(r"^[A-Z]", ln):
            bad.append(ln[:100])
    return bad


print("=== Manual / ad-hoc order line descriptions (no [SKU] prefix) ===")
from datetime import datetime, timedelta
since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
lines = SaleOrderLine.search([
    ("order_id.date_order", ">=", since),
    ("display_type", "=", False),
], order="id desc")
seen = set()
for line in lines:
    name = (line.name or "").strip()
    if not name or name.startswith("[") or name in seen:
        continue
    seen.add(name)
    fs = plain_lines(name)[0] if plain_lines(name) else ""
    if fs and not re.match(r"^[A-Z]", fs):
        print(f"  {line.order_id.name}: {fs!r}")

print("\n=== Product description_sale — body lines not capitalized ===")
count = 0
for p in Product.search([("sale_ok", "=", True), ("website_published", "=", True)]):
    val = p.description_sale or p.description or ""
    bad = bad_lines_in_text(val)
    if bad:
        count += 1
        print(f"  {p.default_code}: {bad[0]!r}" + (f" (+{len(bad)-1} more)" if len(bad) > 1 else ""))
print(f"Products with bad body lines: {count}")
