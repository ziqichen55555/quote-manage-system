# -*- coding: utf-8 -*-
"""Set a new password for Felix Moncrieff (invitation signup is broken).

DRY_RUN=True  → find user, do not write
DRY_RUN=False + confirm_apply=APPLY → write password and cancel signup token
"""
import secrets
import string

DRY_RUN = True
# confirm_apply = APPLY

LOGIN = "felixmoncrieff@cocreativeit.com"

user = env["res.users"].sudo().search([("login", "=", LOGIN)], limit=1)
assert user, "user not found: %s" % LOGIN

print("User id=%s login=%s name=%s active=%s share=%s" % (
    user.id, user.login, user.name, user.active, user.share,
))
print("login_date=%s" % (user.login_date,))
print("partner signup_valid=%s" % (user.partner_id.signup_valid,))
print("DRY_RUN=%s" % DRY_RUN)

if DRY_RUN:
    print("DRY_RUN: would set a new password and cancel signup token.")
else:
    if confirm_apply != "APPLY":
        raise SystemExit("Refusing write without confirm_apply=APPLY")
    alphabet = string.ascii_letters + string.digits
    new_password = "Rw-" + "".join(secrets.choice(alphabet) for _ in range(10))
    user.write({"password": new_password})
    user.partner_id.signup_cancel()
    env.cr.commit()
    print("APPLY done. New password (give to Felix, then change after login):")
    print(new_password)
    print("Login: https://www.reware-project.com/web/login")
    print("Username: %s" % LOGIN)
