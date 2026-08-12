# -*- coding: utf-8 -*-
"""Read-only: mail sender + product/line descriptions missing sentence capitals."""
import re

Company = env["res.company"].sudo()
MailServer = env["ir.mail_server"].sudo()
ICP = env["ir.config_parameter"].sudo()
Product = env["product.template"].sudo()
SaleOrderLine = env["sale.order.line"].sudo()

print("=" * 72)
print("MAIL SENDER")
print("=" * 72)
for c in Company.search([]):
    print(
        f"Company {c.name}: email={c.email!r} website={getattr(c, 'website', None)!r} "
        f"partner_email={c.partner_id.email!r}"
    )
servers = MailServer.search([("active", "=", True)])
print(f"\nActive mail servers: {len(servers)}")
for s in servers:
    print(
        f"  id={s.id} name={s.name!r} smtp_user={s.smtp_user!r} "
        f"from_filter={getattr(s, 'from_filter', None)!r} "
        f"use_microsoft_graph={getattr(s, 'use_microsoft_graph', False)}"
    )
print(f"email_from default param: {ICP.get_param('mail.default.from')!r}")
print(f"catchall: {ICP.get_param('mail.catchall.domain')!r}")

# Pick likely system sender
sender = None
if servers:
    sender = servers[0].smtp_user
if not sender:
    sender = Company.search([], limit=1).email
print(f"\nLIKELY_SENDER: {sender!r}")

print("\n" + "=" * 72)
print("DESCRIPTIONS — first sentence not starting with A-Z")
print("=" * 72)

SENT_START = re.compile(r"^[A-Z]")


def first_sentence(text):
    if not text:
        return ""
    # strip HTML
    plain = re.sub(r"<[^>]+>", " ", text or "")
    plain = plain.replace("\r", "\n")
    # first non-empty line or sentence
    for line in plain.split("\n"):
        line = line.strip()
        if line:
            return line[:120]
    return plain.strip()[:120]


def check_text(label, rec_id, code, field_val):
    fs = first_sentence(field_val)
    if not fs:
        return
    if not SENT_START.match(fs):
        print(f"  [{label}] id={rec_id} code={code!r} -> {fs!r}")


# Product sale descriptions (published shop products)
products = Product.search([
    ("sale_ok", "=", True),
    ("website_published", "=", True),
], order="default_code")
bad_products = 0
for p in products:
    for fname in ("description_sale", "description"):
        val = p[fname]
        if val:
            fs = first_sentence(val)
            if fs and not SENT_START.match(fs):
                bad_products += 1
                check_text("product.template", p.id, p.default_code, val)
                break
print(f"\nPublished sale products checked: {len(products)}; bad first sentence: {bad_products}")

# Recent sale order line names (last 60 days, non-shipping)
from datetime import datetime, timedelta
since = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
lines = SaleOrderLine.search([
    ("order_id.date_order", ">=", since),
    ("display_type", "=", False),
    ("product_id", "!=", False),
], order="id desc", limit=200)
bad_lines = 0
seen = set()
for line in lines:
    name = (line.name or "").strip()
    if not name or name in seen:
        continue
    seen.add(name)
    fs = first_sentence(name)
    if fs and not SENT_START.match(fs):
        bad_lines += 1
        code = line.product_id.default_code or "-"
        print(f"  [sale.order.line] order={line.order_id.name} code={code!r} -> {fs!r}")
print(f"\nRecent order lines sampled: {len(seen)} unique names; bad first sentence: {bad_lines}")
