# -*- coding: utf-8 -*-
"""Public website appointment booking backed by calendar.event."""

from odoo import fields, models


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
