# -*- coding: utf-8 -*-
"""Read-only: who is uid 11 and does Chris have base.group_system?"""
Users = env["res.users"].sudo()
u11 = Users.browse(11)
print(f"User 11: login={u11.login!r} name={u11.name!r} active={u11.active}")
print(f"  share={u11.share} company={u11.company_id.name}")

def dump_user(u):
    groups = u.groups_id.sorted("full_name")
    print(f"\n{u.login} / {u.name} id={u.id}")
    print("  has base.group_system (Administration/Settings)?", u.has_group("base.group_system"))
    print("  has base.group_erp_manager?", u.has_group("base.group_erp_manager"))
    print("  has account.group_account_manager?", u.has_group("account.group_account_manager"))
    print("  has account.group_account_user?", u.has_group("account.group_account_user"))
    interesting = groups.filtered(
        lambda g: any(x in (g.full_name or "").lower() for x in ("admin", "setting", "access", "account", "techn"))
    )
    print("  relevant groups:")
    for g in interesting:
        print(f"    - {g.full_name} ({g.xml_id if g._fields.get('xml_id') else g.id})")

dump_user(u11)

chris = Users.search(["|", ("login", "ilike", "chris"), ("name", "ilike", "chris")])
print(f"\nChris matches: {[(u.id, u.login, u.name) for u in chris]}")
for u in chris:
    dump_user(u)

# Also admin user
admin = Users.browse(2)
if admin.exists():
    dump_user(admin)
