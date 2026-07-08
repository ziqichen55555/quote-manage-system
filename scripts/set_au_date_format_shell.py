# -*- coding: utf-8 -*-
"""Force Odoo date formats to Australian style (day-first)."""

Lang = env["res.lang"].sudo().with_context(active_test=False)

TARGET_DATE_FORMAT = "%d/%m/%Y"
LANG_CODES = ["en_US", "en_AU"]

langs = Lang.search([("code", "in", LANG_CODES)])
if not langs:
    print("No target languages found. Nothing to update.")
else:
    for lang in langs:
        old_fmt = lang.date_format
        if old_fmt != TARGET_DATE_FORMAT:
            lang.write({"date_format": TARGET_DATE_FORMAT})
            print(f"Updated {lang.code}: {old_fmt} -> {TARGET_DATE_FORMAT}")
        else:
            print(f"Already correct {lang.code}: {old_fmt}")

print("Done. Refresh browser / relogin to see changes everywhere.")
