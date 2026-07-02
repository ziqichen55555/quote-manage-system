# -*- coding: utf-8 -*-
inv = env["account.move"].sudo().search([("name", "=", "INV/2026/00017")], limit=1)
mod = env["ir.module.module"].sudo().search([("name", "=", "quote_manage_ui")], limit=1)
company = env.company
print("module:", mod.installed_version)
print("invoice:", inv.name if inv else "NOT FOUND")
if inv:
    company = inv.company_id
print("company:", company.name, "vat:", repr(company.vat))
print("layout:", company.external_report_layout_id.key if company.external_report_layout_id else None)
for xmlid in [
    "quote_manage_ui.external_layout_bold_reware_logo",
    "quote_manage_ui.external_layout_standard_reware_logo",
    "quote_manage_ui.report_invoice_document_payment_details",
]:
    rec = env.ref(xmlid, raise_if_not_found=False)
    print(xmlid, "->", "OK" if rec else "MISSING")
assets = env["ir.asset"].sudo().search([
    ("bundle", "=", "web.report_assets_common"),
    ("path", "ilike", "%report_invoice%"),
])
print("report assets:", assets.mapped("path"))
