# -*- coding: utf-8 -*-
"""Add Administration / Settings to Chris (uid 11).

DRY_RUN=True  → report only
DRY_RUN=False + confirm_apply=APPLY → write group
"""
DRY_RUN = True
# confirm_apply = APPLY

USER_ID = 11
GROUP_XMLID = "base.group_system"

user = env["res.users"].sudo().browse(USER_ID)
group = env.ref(GROUP_XMLID)
assert user.exists(), f"user {USER_ID} missing"
assert group, f"group {GROUP_XMLID} missing"

print(f"User: {user.login} ({user.name}) id={user.id}")
print(f"Group: {group.full_name} ({GROUP_XMLID})")
print(f"Already has group? {group in user.groups_id}")
print(f"has_group before: {user.has_group(GROUP_XMLID)}")

if group in user.groups_id:
    print("Nothing to do.")
elif DRY_RUN:
    print("DRY_RUN: would add group.")
else:
    if confirm_apply != "APPLY":
        raise SystemExit("Refusing write without confirm_apply=APPLY")
    user.write({"groups_id": [(4, group.id)]})
    env.cr.commit()
    user.invalidate_recordset()
    print(f"APPLY done. has_group after: {user.has_group(GROUP_XMLID)}")
    # also show Access Rights group for completeness
    ar = env.ref("base.group_erp_manager", raise_if_not_found=False)
    if ar:
        print(f"Note: also has Access Rights group? {ar in user.groups_id}")
