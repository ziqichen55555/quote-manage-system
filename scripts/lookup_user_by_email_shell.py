# -*- coding: utf-8 -*-
"""Read-only: why password reset might not find a login/email."""
DRY_RUN = True

EMAIL = "ziqichen@cocreativeit.com"
LOGIN_HINT = EMAIL.lower()

User = env["res.users"].sudo().with_context(active_test=False)
Partner = env["res.partner"].sudo().with_context(active_test=False)

print("=== LOOKUP USER / PARTNER (read-only) ===")
print("auth_signup.reset_password param:", env["ir.config_parameter"].get_param("auth_signup.reset_password"))

for label, domain in (
    ("login exact", [("login", "=", EMAIL)]),
    ("login ilike", [("login", "ilike", LOGIN_HINT)]),
    ("email exact", [("email", "=", EMAIL)]),
    ("email ilike", [("email", "ilike", LOGIN_HINT)]),
):
    users = User.search(domain)
    print(f"\nres.users {label}: {len(users)}")
    for u in users:
        print(
            f"  id={u.id} login={u.login!r} email={u.email!r} "
            f"active={u.active} share={u.share} state={getattr(u, 'state', 'n/a')}"
        )

partners = Partner.search([("email", "ilike", LOGIN_HINT)])
print(f"\nres.partner email ilike: {len(partners)}")
for p in partners[:15]:
    linked = User.search([("partner_id", "=", p.id)])
    print(
        f"  partner id={p.id} name={p.name!r} email={p.email!r} "
        f"user_ids={[u.id for u in linked]}"
    )

# Simulate Odoo reset_password search
try:
    u = User
    found = u.search(u._get_login_domain(EMAIL))
    if not found:
        found = u.search(u._get_email_domain(EMAIL))
    print("\nreset_password() would find:", found.ids, found.mapped("login"))
except Exception as e:
    print("\nreset_password simulation error:", e)

u11 = User.browse(11)
if u11.exists():
    print(f"\nUser id=11: login={u11.login!r} email={u11.email!r} active={u11.active}")

for attempt in (
    "ziqichen@cocreativeit.com",
    "chrischen",
    "Chris",
    "intern@cocreativeit.com",
):
    found = User.search(User._get_login_domain(attempt))
    if not found:
        found = User.search(User._get_email_domain(attempt))
    print(f"reset_password({attempt!r}) -> ids={found.ids} logins={found.mapped('login')}")

print("Done.")
