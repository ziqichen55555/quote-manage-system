# -*- coding: utf-8 -*-
"""1.0.166 — Add appointment team as attendees on future website bookings."""

from odoo import SUPERUSER_ID, api, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    team = env['res.config.settings'].get_appointment_team_users()
    partner_ids = team.partner_id.ids
    if not partner_ids:
        return

    events = env['calendar.event'].sudo().search([
        ('x_is_website_booking', '=', True),
        ('active', '=', True),
        ('start', '>=', fields.Datetime.now()),
    ])
    for event in events:
        missing = [pid for pid in partner_ids if pid not in event.partner_ids.ids]
        if missing:
            event.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
            ).write({'partner_ids': [(4, pid) for pid in missing]})
