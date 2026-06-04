"""Set up Re-Ware company + users. Run via `odoo shell` on the server.

Idempotent: safe to re-run. It will
  1. Stamp the main company with Re-Ware details + address.
  2. Convert the existing admin user into the "Re-Ware" user
     (login -> re-ware@cocreativeit.com), keeping its current password.
  3. Create Louis Moncrieff and Drew Wright as full administrators
     (groups copied from the admin user) with a temporary password.

Env overrides:
  TEMP_PASSWORD  temporary password for the two new users (default below)
"""
import os

TEMP_PASSWORD = os.environ.get("TEMP_PASSWORD") or "ReWare-2026!"

COMPANY = {
    "name": "Re-Ware",
    "email": "re-ware@cocreativeit.com",
    "phone": "0499 909 302",
    "street": "102 Edward St",
    "city": "Perth",
    "state_name": "Western Australia",
    "country_code": "AU",
}

# login -> display name. The first entry is the renamed admin.
ADMIN_LOGIN = "re-ware@cocreativeit.com"
ADMIN_NAME = "Re-Ware"
NEW_USERS = [
    {"login": "louismoncrieff@cocreativeit.com", "name": "Louis Moncrieff"},
    {"login": "drewwright@cocreativeit.com", "name": "Drew Wright"},
]


def run(env):
    Users = env["res.users"].sudo()
    Partner = env["res.partner"].sudo()

    admin = env.ref("base.user_admin")
    company = admin.company_id or env.ref("base.main_company")
    company = company.sudo()

    # --- 1. Company details + address -------------------------------------
    country = env["res.country"].sudo().search(
        [("code", "=", COMPANY["country_code"])], limit=1)
    state = env["res.country.state"].sudo().search(
        [("country_id", "=", country.id), ("name", "=", COMPANY["state_name"])],
        limit=1) if country else env["res.country.state"]

    address_vals = {
        "street": COMPANY["street"],
        "city": COMPANY["city"],
        "country_id": country.id if country else False,
        "state_id": state.id if state else False,
    }
    company.write(dict(
        name=COMPANY["name"],
        email=COMPANY["email"],
        phone=COMPANY["phone"],
        **address_vals,
    ))
    print(f"[company] {company.name} @ {COMPANY['street']}, "
          f"{COMPANY['city']}, {COMPANY['state_name']}")

    # Full-admin group set, copied from the existing admin user.
    admin_group_ids = admin.groups_id.ids

    # --- 2. Convert admin -> Re-Ware user ---------------------------------
    # Keep the current password; only the login/name/email change.
    clash = Users.search(
        [("login", "=", ADMIN_LOGIN), ("id", "!=", admin.id)], limit=1)
    if clash:
        print(f"[admin] WARNING: login {ADMIN_LOGIN} already used by "
              f"user id={clash.id}; leaving admin login unchanged.")
    else:
        admin.write({"name": ADMIN_NAME, "login": ADMIN_LOGIN})
    admin.partner_id.write({
        "name": ADMIN_NAME,
        "email": COMPANY["email"],
        "phone": COMPANY["phone"],
        **address_vals,
    })
    print(f"[admin] id={admin.id} -> name={ADMIN_NAME!r} "
          f"login={admin.login!r} (password unchanged)")

    # --- 3. Create / update the two new admins ----------------------------
    for spec in NEW_USERS:
        user = Users.search([("login", "=", spec["login"])], limit=1)
        vals = {
            "name": spec["name"],
            "login": spec["login"],
            "email": spec["login"],
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "groups_id": [(6, 0, admin_group_ids)],
        }
        if user:
            user.write(vals)
            action = "updated"
        else:
            vals["password"] = TEMP_PASSWORD
            user = Users.create(vals)
            action = "created"
        user.partner_id.write(address_vals)
        print(f"[user] {action}: id={user.id} {spec['name']!r} "
              f"login={spec['login']!r}")

    env.cr.commit()
    print("\nDone. Temporary password for the two NEW users "
          f"(Louis & Drew): {TEMP_PASSWORD!r}")
    print("Admin/Re-Ware login: " + ADMIN_LOGIN +
          " (its existing password is unchanged).")


run(env)  # noqa: F821  (`env` is provided by `odoo shell`)
