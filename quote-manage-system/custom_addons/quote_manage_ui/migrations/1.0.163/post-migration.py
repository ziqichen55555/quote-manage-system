# -*- coding: utf-8 -*-
"""1.0.163 — Team calendar invites, company address, two phone footer."""
from odoo import api, fields, SUPERUSER_ID

_TEAM_PARAM = 'quote_manage_ui.appointment_team_user_ids'
_DEFAULT_TEAM_LOGINS = (
    're-ware@cocreativeit.com',
    'louismoncrieff@cocreativeit.com',
    'drewwright@cocreativeit.com',
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.company.sudo()
    if company:
        updates = {}
        if not company.mobile:
            updates['mobile'] = '0499 909 302'
        if not company.phone:
            updates['phone'] = '0411 882 377'
        if updates:
            company.write(updates)

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

    CalendarEvent = env['calendar.event'].sudo()
    location = CalendarEvent._format_company_address(company)
    bookings = CalendarEvent.search([
        ('x_is_website_booking', '=', True),
        ('active', '=', True),
        ('start', '>', fields.Datetime.now()),
    ])
    for event in bookings:
        vals = {'x_booking_invite_sent': False}
        if location:
            vals['location'] = location
        event.with_context(
            no_mail_to_attendees=True,
            dont_notify=True,
        ).write(vals)
