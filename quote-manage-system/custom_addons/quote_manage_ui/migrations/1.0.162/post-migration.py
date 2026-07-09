# -*- coding: utf-8 -*-
"""1.0.162 — Guest-only invitees; 30-minute reminder cron."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    bookings = env['calendar.event'].sudo().search([
        ('x_is_website_booking', '=', True),
        ('active', '=', True),
    ])
    for event in bookings:
        organizer = event.user_id.partner_id
        guests = event.partner_ids - organizer
        if guests != event.partner_ids:
            event.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
            ).write({
                'partner_ids': [(6, 0, guests.ids)],
                'x_booking_invite_sent': False,
            })
