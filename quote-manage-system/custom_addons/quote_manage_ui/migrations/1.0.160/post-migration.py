# -*- coding: utf-8 -*-
"""1.0.160 — Default appointment team + invite team on existing bookings."""
from odoo import api, SUPERUSER_ID

_TEAM_PARAM = 'quote_manage_ui.appointment_team_user_ids'
_DEFAULT_TEAM_LOGINS = (
    're-ware@cocreativeit.com',
    'louismoncrieff@cocreativeit.com',
    'drewwright@cocreativeit.com',
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Icp = env['ir.config_parameter'].sudo()
    if not Icp.get_param(_TEAM_PARAM):
        team = env['res.users'].sudo().search([
            ('login', 'in', list(_DEFAULT_TEAM_LOGINS)),
            ('share', '=', False),
            ('active', '=', True),
        ])
        if team:
            Icp.set_param(
                _TEAM_PARAM,
                ','.join(str(user.id) for user in team),
            )

    team = env['res.config.settings'].get_appointment_team_users()
    team_partners = team.partner_id
    bookings = env['calendar.event'].sudo().search([
        ('x_is_website_booking', '=', True),
        ('active', '=', True),
    ])
    for event in bookings:
        missing = team_partners - event.partner_ids
        if missing:
            event.write({
                'partner_ids': [(4, partner.id) for partner in missing],
            })
