# -*- coding: utf-8 -*-
"""1.0.167 — Restore team attendees on all active website bookings."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
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
