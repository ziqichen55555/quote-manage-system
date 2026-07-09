# -*- coding: utf-8 -*-
"""1.0.168 — Force mandatory team visibility for website bookings."""

from odoo import SUPERUSER_ID, api

_TEAM_PARAM = 'quote_manage_ui.appointment_team_user_ids'
_DEFAULT_TEAM_LOGINS = (
    're-ware@cocreativeit.com',
    'louismoncrieff@cocreativeit.com',
    'drewwright@cocreativeit.com',
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Users = env['res.users'].sudo()
    mandatory_users = Users.search([
        ('login', 'in', list(_DEFAULT_TEAM_LOGINS)),
        ('share', '=', False),
        ('active', '=', True),
    ])
    mandatory_ids = set(mandatory_users.ids)

    Icp = env['ir.config_parameter'].sudo()
    raw = Icp.get_param(_TEAM_PARAM, '') or ''
    configured_ids = {int(uid) for uid in raw.split(',') if uid.strip().isdigit()}
    merged_ids = sorted(configured_ids | mandatory_ids)
    if merged_ids:
        Icp.set_param(_TEAM_PARAM, ','.join(str(uid) for uid in merged_ids))

    team = env['res.config.settings'].get_appointment_team_users()
    team_partner_ids = team.partner_id.ids
    if not team_partner_ids:
        return

    events = env['calendar.event'].sudo().search([
        ('x_is_website_booking', '=', True),
        ('active', '=', True),
    ])
    for event in events:
        existing = set(event.partner_ids.ids)
        missing = [pid for pid in team_partner_ids if pid not in existing]
        if missing:
            event.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
            ).write({'partner_ids': [(4, pid) for pid in missing]})
