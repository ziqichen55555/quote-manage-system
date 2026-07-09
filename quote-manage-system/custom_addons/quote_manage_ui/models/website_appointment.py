# -*- coding: utf-8 -*-
"""Public website appointment booking backed by calendar.event."""

from odoo import api, fields, models

_APPOINTMENT_CALENDAR_USER_PARAM = 'quote_manage_ui.appointment_calendar_user_id'
_APPOINTMENT_TEAM_USER_IDS_PARAM = 'quote_manage_ui.appointment_team_user_ids'
_DEFAULT_TEAM_LOGINS = (
    're-ware@cocreativeit.com',
    'louismoncrieff@cocreativeit.com',
    'drewwright@cocreativeit.com',
)


class WebsiteAppointmentType(models.Model):
    _name = 'website.appointment.type'
    _description = 'Website Appointment Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    duration_minutes = fields.Integer(default=30, required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    x_is_website_booking = fields.Boolean(
        string='Website Booking',
        default=False,
        index=True,
    )
    x_booking_email = fields.Char(string='Booking Email', index=True)
    x_appointment_type_id = fields.Many2one(
        'website.appointment.type',
        string='Appointment Type',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appointment_calendar_user_id = fields.Many2one(
        'res.users',
        string='Website Appointment Calendar',
        domain=[('share', '=', False), ('active', '=', True)],
        config_parameter=_APPOINTMENT_CALENDAR_USER_PARAM,
        help='Organizer for public bookings. Usually the shared Re-Ware account. '
             'Team members view this calendar in Odoo — no invitations are sent.',
    )
    appointment_team_user_ids = fields.Many2many(
        'res.users',
        string='Appointment team',
        domain=[('share', '=', False), ('active', '=', True)],
        help='Used only to block busy time slots. These users are not emailed '
             'and are not added as meeting attendees. Everyone sees bookings on '
             'the organizer calendar (enable Everyone\'s calendars in Calendar).',
    )

    def get_values(self):
        res = super().get_values()
        raw = self.env['ir.config_parameter'].sudo().get_param(
            _APPOINTMENT_TEAM_USER_IDS_PARAM,
            '',
        )
        user_ids = [int(uid) for uid in raw.split(',') if uid.strip().isdigit()]
        res['appointment_team_user_ids'] = [(6, 0, user_ids)]
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            _APPOINTMENT_TEAM_USER_IDS_PARAM,
            ','.join(str(uid) for uid in self.appointment_team_user_ids.ids),
        )

    @api.model
    def _default_appointment_team_users(self):
        Users = self.env['res.users'].sudo()
        team = Users.search([
            ('login', 'in', list(_DEFAULT_TEAM_LOGINS)),
            ('share', '=', False),
            ('active', '=', True),
        ])
        if team:
            return team
        return Users.search([
            ('share', '=', False),
            ('active', '=', True),
        ])

    @api.model
    def get_appointment_team_users(self):
        """Internal users who receive and block website bookings."""
        raw = self.env['ir.config_parameter'].sudo().get_param(
            _APPOINTMENT_TEAM_USER_IDS_PARAM,
            '',
        )
        user_ids = [int(uid) for uid in raw.split(',') if uid.strip().isdigit()]
        team = self.env['res.users'].browse(user_ids).exists().filtered(
            lambda user: user.active and not user.share,
        )
        if team:
            return team
        calendar_user = self.get_appointment_calendar_user()
        if calendar_user:
            return calendar_user
        return self._default_appointment_team_users()

    @api.model
    def get_appointment_calendar_user(self):
        """Return the internal user that owns public website bookings."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            _APPOINTMENT_CALENDAR_USER_PARAM,
        )
        user = self.env['res.users'].browse(int(param)).exists() if param else False
        if user and user.active and not user.share:
            return user
        return self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ], limit=1, order='id')
