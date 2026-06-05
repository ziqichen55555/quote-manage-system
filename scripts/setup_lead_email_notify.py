"""Email re-ware, Louis & Drew whenever a WEBSITE FORM creates a crm.lead.

Website forms (Contact / Our Why pages) post to /website/form/ and create a
crm.lead. website_crm stamps those leads with medium_id = "Website"
(utm.utm_medium_website), which lets us target ONLY form submissions and skip
manually-created pipeline leads.

This script (idempotent) creates:
  1. A mail.template on crm.lead addressed to the three mailboxes.
  2. A base.automation (trigger on_create, filtered to the Website medium)
     whose server action sends that template by email.

Run via `odoo shell` on the server.
"""

RULE_NAME = "Notify team on website enquiry"
TEMPLATE_NAME = "Re-Ware: New Website Enquiry Notification"
# re-ware is the SENDER only, never a recipient (it only receives genuine
# replies addressed to it). Notifications go to Louis & Drew.
NOTIFY_EMAILS = [
    "louismoncrieff@cocreativeit.com",
    "drewwright@cocreativeit.com",
]

SUBJECT = "New website enquiry: {{ object.name or 'Contact form' }}"

BODY_HTML = """
<div style="margin:0;padding:0;font-size:13px;">
    <p>A new enquiry was submitted on the Re-Ware website.</p>
    <table style="border-collapse:collapse;font-size:13px;">
        <tr><td style="padding:2px 12px 2px 0;"><strong>Enquiry</strong></td>
            <td t-out="object.name or ''">Contact form</td></tr>
        <tr><td style="padding:2px 12px 2px 0;"><strong>First name</strong></td>
            <td t-out="object.contact_name or ''"></td></tr>
        <tr><td style="padding:2px 12px 2px 0;"><strong>Last name</strong></td>
            <td t-out="object.partner_name or ''"></td></tr>
        <tr><td style="padding:2px 12px 2px 0;"><strong>Email</strong></td>
            <td t-out="object.email_from or ''"></td></tr>
        <tr><td style="padding:2px 12px 2px 0;"><strong>Phone</strong></td>
            <td t-out="object.phone or ''"></td></tr>
        <tr><td style="padding:2px 12px 2px 0;vertical-align:top;"><strong>Message</strong></td>
            <td t-out="object.description or ''"></td></tr>
        <tr><td style="padding:2px 12px 2px 0;"><strong>Received</strong></td>
            <td t-out="object.create_date or ''"></td></tr>
    </table>
    <p style="margin-top:12px;">Open it in the CRM pipeline to follow up.</p>
</div>
"""


def run(env):
    crm_model = env["ir.model"].sudo().search([("model", "=", "crm.lead")], limit=1)
    if not crm_model:
        print("[lead-notify] crm.lead model not found; is CRM installed? Aborting.")
        return

    website_medium = env.ref("utm.utm_medium_website", raise_if_not_found=False)
    if not website_medium:
        print("[lead-notify] utm.utm_medium_website not found; aborting.")
        return

    company = env.ref("base.main_company")
    # re-ware is always the sender.
    from_email = company.email or "re-ware@cocreativeit.com"

    # --- 1. Mail template -------------------------------------------------
    Template = env["mail.template"].sudo()
    template = Template.search([("name", "=", TEMPLATE_NAME)], limit=1)
    tmpl_vals = {
        "name": TEMPLATE_NAME,
        "model_id": crm_model.id,
        "subject": SUBJECT,
        "email_from": f"{from_email}",
        "email_to": ",".join(NOTIFY_EMAILS),
        "use_default_to": False,
        "partner_to": False,
        "body_html": BODY_HTML,
        "auto_delete": True,
        "lang": "{{ object.lang_id.code or 'en_US' }}",
    }
    if template:
        template.write(tmpl_vals)
        print(f"[lead-notify] template updated: id={template.id}")
    else:
        template = Template.create(tmpl_vals)
        print(f"[lead-notify] template created: id={template.id}")

    # --- 2. Server action + automation rule -------------------------------
    server_action_vals = {
        "name": "Email team about website enquiry",
        "state": "mail_post",
        "model_id": crm_model.id,
        "usage": "base_automation",
        "template_id": template.id,
        "mail_post_method": "email",
    }

    Automation = env["base.automation"].sudo()
    rule = Automation.search([("name", "=", RULE_NAME)], limit=1)
    if rule:
        rule.write({
            "model_id": crm_model.id,
            "trigger": "on_create",
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
            "model_id": crm_model.id,
            "trigger": "on_create",
            "active": True,
            "action_server_ids": [(0, 0, server_action_vals)],
        })
        action = "created"

    # filter_domain is computed-stored (depends on trigger/trigger_field_ids);
    # for on_create it gets reset to False, so set it explicitly afterwards to
    # only fire for leads created through the website forms.
    rule.filter_domain = f"[('medium_id', '=', {website_medium.id})]"

    env.cr.commit()
    print(f"[lead-notify] rule {action}: id={rule.id} {RULE_NAME!r}")
    print(f"[lead-notify] trigger={rule.trigger} filter_domain={rule.filter_domain!r}")
    print(f"[lead-notify] recipients={NOTIFY_EMAILS}")


run(env)  # noqa: F821  (`env` provided by `odoo shell`)
