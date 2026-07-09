# -*- coding: utf-8 -*-
"""Public website appointment booking backed by calendar.event."""

from odoo import api, fields, models

_APPOINTMENT_CALENDAR_USER_PARAM = 'quote_manage_ui.appointment_calendar_user_id'


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
        help='Bookings from the public page are created on this user calendar.',
    )

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
