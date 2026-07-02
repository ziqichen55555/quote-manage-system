# -*- coding: utf-8 -*-
"""Inspect invoice PDF layout: company ABN, logo, report layout, module version."""
import re

inv = env["account.move"].sudo().search(
    [("name", "ilike", "%00017")], order="id desc", limit=1
)
if not inv:
  inv = env["account.move"].sudo().search(
      [("move_type", "=", "out_invoice")], order="invoice_date desc, id desc", limit=1
  )

mod = env["ir.module.module"].sudo().search([("name", "=", "quote_manage_ui")], limit=1)
company = inv.company_id if inv else env.company

print("=== MODULE ===")
print("quote_manage_ui installed:", mod.state, "version:", mod.installed_version, "latest:", mod.latest_version)

print("\n=== INVOICE ===")
if inv:
    print("name:", inv.name, "state:", inv.state, "company:", inv.company_id.name)
else:
    print("NO INVOICE FOUND")

print("\n=== COMPANY ===")
print("id:", company.id, "name:", company.name)
print("country:", company.country_id.code, company.country_id.name)
print("vat (ABN):", repr(company.vat))
print("partner.vat:", repr(company.partner_id.vat))
print("company_registry (ACN):", repr(company.company_registry))
print("has logo:", bool(company.logo))
if company.logo:
    print("logo bytes:", len(company.logo))
print("external_report_layout:", company.external_report_layout_id.key if company.external_report_layout_id else None)
print("layout_background:", company.layout_background)
print("is_company_details_empty:", company.is_company_details_empty)
details = company.company_details or ""
print("company_details len:", len(details))
if details:
    print("company_details snippet:", re.sub(r"\s+", " ", details)[:200])

print("\n=== TEMPLATE INHERITS ===")
for xmlid in [
    "quote_manage_ui.external_layout_standard_reware_logo",
    "quote_manage_ui.external_layout_boxed_reware_logo",
    "quote_manage_ui.report_invoice_document_payment_details",
]:
    rec = env.ref(xmlid, raise_if_not_found=False)
    print(xmlid, "->", "OK" if rec else "MISSING", "active:", rec.active if rec else None)

print("\n=== REPORT ASSETS ===")
assets = env["ir.asset"].sudo().search([
    ("bundle", "=", "web.report_assets_common"),
    ("path", "ilike", "quote_manage_ui%report_invoice"),
])
for a in assets:
    print(a.name, a.path, "active:", a.active)

print("\nDone.")
