# -*- coding: utf-8 -*-
"""Public website appointment booking backed by calendar.event."""

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_APPOINTMENT_CALENDAR_USER_PARAM = 'quote_manage_ui.appointment_calendar_user_id'
_APPOINTMENT_TEAM_USER_IDS_PARAM = 'quote_manage_ui.appointment_team_user_ids'
_DEFAULT_TEAM_LOGINS = (
    're-ware@cocreativeit.com',
    'louismoncrieff@cocreativeit.com',
    'drewwright@cocreativeit.com',
    'chrischen@cocreativeit.com',
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
    x_booking_invite_sent = fields.Boolean(
        string='Website Reminder Sent',
        default=False,
        index=True,
        help='Set when the 30-minute reminder / calendar invite was emailed.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('x_is_website_booking') for vals in vals_list):
            self = self.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
                mail_create_nolog=True,
            )
        return super().create(vals_list)

    @api.model
    def _format_company_address(self, company):
        """Single-line postal address from the company record."""
        if not company:
            return ''
        parts = [
            company.street,
            company.street2,
            company.city,
            company.state_id.code if company.state_id else '',
            company.zip,
        ]
        line = ', '.join(part for part in parts if part)
        if company.country_id:
            country = company.country_id.name
            if country and country not in line:
                line = ', '.join(part for part in [line, country] if part)
        return line

    def _sync_website_booking_location(self):
        """Refresh event location from company address (for email + ICS)."""
        self.ensure_one()
        location = self._format_company_address(self.user_id.company_id)
        if location and self.location != location:
            self.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
            ).write({'location': location})

    def _website_booking_guest_partners(self):
        self.ensure_one()
        organizer_partner = self.user_id.partner_id
        guests = self.partner_ids - organizer_partner
        guests = guests.filtered('email')
        if guests:
            return guests
        if not self.x_booking_email:
            return self.env['res.partner']
        return self.env['res.partner'].search([
            ('email', '=ilike', self.x_booking_email),
        ], limit=1)

    def _ensure_website_booking_invite_attendees(self):
        """Attendee rows for team + guest; no invitation emails on this step."""
        self.ensure_one()
        team = self.env['res.config.settings'].get_appointment_team_users()
        partners = team.partner_id | self._website_booking_guest_partners()
        missing = partners - self.partner_ids
        if missing:
            self.with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
            ).write({'partner_ids': [(4, partner.id) for partner in missing]})
        return self.attendee_ids.filtered(lambda attendee: attendee.partner_id in partners)

    def _send_website_booking_invite(self):
        """Email calendar invites ~30 minutes before the appointment."""
        self.ensure_one()
        if self.x_booking_invite_sent or not self.x_is_website_booking or not self.active:
            return False
        template = self.env.ref(
            'quote_manage_ui.mail_template_website_booking_reminder',
            raise_if_not_found=False,
        )
        if not template:
            return False
        self._sync_website_booking_location()
        recipients = self._ensure_website_booking_invite_attendees()
        if not recipients:
            return False
        recipients.with_context(mail_notify_author=True)._send_mail_to_attendees(
            template,
            force_send=True,
        )
        self.sudo().write({'x_booking_invite_sent': True})
        return True

    @api.model
    def _cron_send_website_booking_invites(self):
        """Send calendar invites when an appointment is about 30 minutes away."""
        now = fields.Datetime.now()
        horizon = now + timedelta(minutes=30)
        events = self.sudo().search([
            ('x_is_website_booking', '=', True),
            ('active', '=', True),
            ('x_booking_invite_sent', '=', False),
            ('start', '>', now),
            ('start', '<=', horizon),
        ])
        for event in events:
            try:
                event._send_website_booking_invite()
            except Exception:
                _logger.exception(
                    'Website booking invite failed for event %s',
                    event.id,
                )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appointment_calendar_user_id = fields.Many2one(
        'res.users',
        string='Website Appointment Calendar',
        domain=[('share', '=', False), ('active', '=', True)],
        config_parameter=_APPOINTMENT_CALENDAR_USER_PARAM,
        help='Organizer for public bookings. Usually the shared Re-Ware account.',
    )
    appointment_team_user_ids = fields.Many2many(
        'res.users',
        string='Appointment team',
        domain=[('share', '=', False), ('active', '=', True)],
        help='These users receive the calendar invite 30 minutes before each '
             'website booking, and their calendars are checked for availability.',
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
    def _mandatory_appointment_team_users(self):
        """Core team that must always see website bookings in Calendar."""
        return self.env['res.users'].sudo().search([
            ('login', 'in', list(_DEFAULT_TEAM_LOGINS)),
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
        configured = self.env['res.users'].browse(user_ids).exists().filtered(
            lambda user: user.active and not user.share,
        )
        team = configured | self._mandatory_appointment_team_users()
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
