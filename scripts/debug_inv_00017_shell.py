# -*- coding: utf-8 -*-
inv = env["account.move"].sudo().search([("name", "=", "INV/2026/00017")], limit=1)
if not inv:
    inv = env["account.move"].sudo().search(
        [("name", "ilike", "INV/2026/00017")], limit=1
    )
print("invoice:", inv.name if inv else "NOT FOUND")
if inv:
    c = inv.company_id
    print("company:", c.name)
    print("vat:", repr(c.vat))
    print("layout:", c.external_report_layout_id.key if c.external_report_layout_id else None)
