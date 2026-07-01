# -*- coding: utf-8 -*-
"""Add BSB Bank Transfer inbound payment method line on BNK1 (Manual + custom name)."""
Journal = env["account.journal"].sudo()
Method = env["account.payment.method"].sudo()
Line = env["account.payment.method.line"].sudo()

journal = Journal.search([("code", "=", "BNK1")], limit=1)
if not journal:
    journal = Journal.search([("type", "=", "bank")], limit=1)
if not journal:
    print("No bank journal found")
else:
    print(f"Journal: {journal.name} ({journal.code}) id={journal.id}")
    print("Before:")
    for line in journal.inbound_payment_method_line_ids:
        pm = line.payment_method_id
        print(f"  line id={line.id}  name={line.name!r}  method={pm.name if pm else '-'} code={pm.code if pm else '-'}")

    existing = journal.inbound_payment_method_line_ids.filtered(
        lambda l: (l.name or "").strip().casefold() == "bsb bank transfer"
    )
    if existing:
        print(f"Already exists: {existing[0].name} (id={existing[0].id})")
    else:
        manual = Method.search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")], limit=1
        )
        if not manual:
            print("ERROR: inbound manual payment method not found")
        else:
            new_line = Line.create(
                {
                    "name": "BSB Bank Transfer",
                    "payment_method_id": manual.id,
                    "journal_id": journal.id,
                    "payment_type": "inbound",
                }
            )
            print(f"Created payment method line id={new_line.id} name={new_line.name!r}")

    print("After:")
    for line in journal.inbound_payment_method_line_ids:
        pm = line.payment_method_id
        print(f"  line id={line.id}  name={line.name!r}  method={pm.name if pm else '-'} code={pm.code if pm else '-'}")

if not env.context.get("dry_run"):
    env.cr.commit()
    print("Committed.")
else:
    env.cr.rollback()
print("Done.")
