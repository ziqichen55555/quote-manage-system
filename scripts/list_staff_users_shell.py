# -*- coding: utf-8 -*-
"""Read-only: list Re-Ware staff users."""
Users = env["res.users"].sudo()
Team = env["crm.team"].sudo()
Website = env["website"].sudo()

print("=== Website sales team ===")
for w in Website.search([]):
  print(f"Website: {w.name}")
  print(f"  salesperson_id: {w.salesperson_id.login if w.salesperson_id else None} ({w.salesperson_id.name if w.salesperson_id else '-'})")
  print(f"  salesteam_id: {w.salesteam_id.name if w.salesteam_id else None}")

print("\n=== CRM / Sales teams ===")
for t in Team.search([]):
  members = t.member_ids
  print(f"Team: {t.name} id={t.id} user_id={t.user_id.login if t.user_id else '-'}")
  for u in members:
    print(f"  member: {u.login} ({u.name}) active={u.active} share={u.share}")

print("\n=== Internal users (not portal/public) ===")
internal = Users.search([
    ("share", "=", False),
    ("active", "=", True),
    ("id", "not in", [1, 2]),  # skip generic admin templates if desired
])
for u in internal.sorted(lambda x: x.name):
    groups = u.groups_id.filtered(lambda g: "Sales" in g.full_name or "Inventory" in g.full_name or "Administration" in g.full_name)
    gnames = ", ".join(g.full_name for g in groups[:6])
    print(f"  {u.login} | {u.name} | company={u.company_id.name} | {gnames}")

print("\n=== Order notify email (staff inbox) ===")
icp = env["ir.config_parameter"].sudo().get_param("quote_manage_ui.website_order_notify_email", "(not set)")
print(f"  {icp}")
