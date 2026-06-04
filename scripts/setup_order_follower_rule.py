"""Create an Automated Action: when a Sale Order is confirmed (state -> sale),
add Louis Moncrieff and Drew Wright as followers so they get notified.

Run via `odoo shell` on the server. Idempotent: re-running updates the
existing rule rather than creating duplicates.
"""

RULE_NAME = "Notify Louis & Drew on order confirmation"
FOLLOWER_LOGINS = [
    "louismoncrieff@cocreativeit.com",
    "drewwright@cocreativeit.com",
]


def run(env):
    Users = env["res.users"].sudo()
    partners = env["res.partner"]
    for login in FOLLOWER_LOGINS:
        user = Users.search([("login", "=", login)], limit=1)
        if not user:
            print(f"[rule] WARNING: user not found: {login}")
            continue
        partners |= user.partner_id
    if not partners:
        print("[rule] No partners resolved; aborting.")
        return

    so_model = env["ir.model"].sudo().search([("model", "=", "sale.order")], limit=1)

    # The 'state' field that the on_state_set trigger watches.
    state_field = env["ir.model.fields"].sudo().search([
        ("model", "=", "sale.order"),
        ("name", "=", "state"),
    ], limit=1)

    # Selection value (state == 'sale') used by the on_state_set trigger.
    sale_state = env["ir.model.fields.selection"].sudo().search([
        ("field_id.model", "=", "sale.order"),
        ("field_id.name", "=", "state"),
        ("value", "=", "sale"),
    ], limit=1)

    Automation = env["base.automation"].sudo()
    rule = Automation.search([("name", "=", RULE_NAME)], limit=1)

    server_action_vals = {
        "name": "Add Louis & Drew as followers",
        "state": "followers",
        "model_id": so_model.id,
        "usage": "base_automation",
        "partner_ids": [(6, 0, partners.ids)],
    }

    if rule:
        rule.write({
            "model_id": so_model.id,
            "trigger": "on_state_set",
            "active": True,
        })
        if rule.action_server_ids:
            rule.action_server_ids[0].write(server_action_vals)
        else:
            rule.write({"action_server_ids": [(0, 0, server_action_vals)]})
        action = "updated"
    else:
        rule = Automation.create({
            "name": RULE_NAME,
            "model_id": so_model.id,
            "trigger": "on_state_set",
            "active": True,
            "action_server_ids": [(0, 0, server_action_vals)],
        })
        action = "created"

    # `trigger` and `trigger_field_ids` share one compute method; passing
    # `trigger` explicitly in create makes Odoo skip the compute, leaving
    # trigger_field_ids empty (-> filter_domain stays False). Set both watched
    # field + selection value explicitly. Order matters: writing
    # trigger_field_ids resets trg_selection_field_id (its @api.depends), so
    # the selection value MUST be written afterwards.
    rule.trigger_field_ids = [(6, 0, state_field.ids)]
    rule.trg_selection_field_id = sale_state.id

    env.cr.commit()
    print(f"[rule] {action}: id={rule.id} {RULE_NAME!r}")
    print(f"[rule] trigger={rule.trigger} filter_domain={rule.filter_domain!r}")
    print(f"[rule] followers={partners.mapped('name')} "
          f"({partners.mapped('email')})")


run(env)  # noqa: F821  (`env` provided by `odoo shell`)
