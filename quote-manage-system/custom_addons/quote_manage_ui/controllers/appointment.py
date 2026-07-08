# -*- coding: utf-8 -*-
"""Public appointment booking page — create / cancel calendar.event records."""

import logging
import re
from datetime import datetime, time, timedelta

import pytz

from odoo import _, fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_WORK_START_HOUR = 9
_WORK_END_HOUR = 17
_SLOT_MINUTES = 30
_BOOKING_HORIZON_DAYS = 30


class WebsiteAppointmentController(http.Controller):

    def _booking_env(self):
        return request.env(su=True)

    def _booking_tz(self, env):
        tz_name = (
            env.company.resource_calendar_id.tz
            or env.user.tz
            or 'Australia/Sydney'
        )
        return pytz.timezone(tz_name)

    def _localize_slot(self, tz, day, hour, minute):
        naive = datetime.combine(day, time(hour, minute))
        return tz.localize(naive)

    def _slot_busy(self, events, slot_start, slot_stop):
        for event in events:
            if event.allday:
                return True
            if event.start < slot_stop and event.stop > slot_start:
                return True
        return False

    def _get_staff_users(self, env):
        return env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ], order='name')

    def _get_appointment_types(self, env):
        return env['website.appointment.type'].search([
            ('active', '=', True),
        ])

    def _serialize_types(self, types):
        return [{
            'id': rec.id,
            'name': rec.name,
            'duration_minutes': rec.duration_minutes,
        } for rec in types]

    def _serialize_staff(self, users):
        return [{
            'id': user.id,
            'name': user.name,
        } for user in users]

    def _serialize_dates(self, tz):
        today = datetime.now(tz).date()
        options = []
        cursor = today
        while len(options) < _BOOKING_HORIZON_DAYS:
            if cursor.weekday() < 5:
                options.append({
                    'value': cursor.isoformat(),
                    'label': cursor.strftime('%a, %d %b %Y'),
                })
            cursor += timedelta(days=1)
        return options

    @http.route(
        '/quote_manage_ui/appointment/bootstrap',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def appointment_bootstrap(self, **post):
        env = self._booking_env()
        types = self._get_appointment_types(env)
        staff = self._get_staff_users(env)
        if not types:
            return {
                'success': False,
                'message': _('No appointment types are configured yet.'),
            }
        if not staff:
            return {
                'success': False,
                'message': _('No staff members are available for booking.'),
            }
        tz = self._booking_tz(env)
        return {
            'success': True,
            'types': self._serialize_types(types),
            'staff': self._serialize_staff(staff),
            'dates': self._serialize_dates(tz),
        }

    @http.route(
        '/quote_manage_ui/appointment/slots',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def appointment_slots(self, **post):
        env = self._booking_env()
        user_id = int(post.get('user_id') or 0)
        date_str = (post.get('date') or '').strip()
        type_id = int(post.get('appointment_type_id') or 0)

        staff = env['res.users'].browse(user_id).exists()
        apt_type = env['website.appointment.type'].browse(type_id).exists()
        if not staff or not staff.active or staff.share:
            return {'success': False, 'message': _('Please choose a staff member.')}
        if not apt_type or not apt_type.active:
            return {'success': False, 'message': _('Please choose an appointment type.')}

        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return {'success': False, 'message': _('Please choose a valid date.')}

        tz = self._booking_tz(env)
        today = datetime.now(tz).date()
        if day < today or day.weekday() >= 5:
            return {'success': False, 'message': _('Please choose a future weekday.')}

        duration = apt_type.duration_minutes
        day_start = self._localize_slot(tz, day, _WORK_START_HOUR, 0)
        day_end = self._localize_slot(tz, day, _WORK_END_HOUR, 0)
        utc_start = day_start.astimezone(pytz.utc).replace(tzinfo=None)
        utc_end = day_end.astimezone(pytz.utc).replace(tzinfo=None)

        events = env['calendar.event'].search([
            ('user_id', '=', staff.id),
            ('active', '=', True),
            ('start', '<', utc_end),
            ('stop', '>', utc_start),
        ])

        slots = []
        cursor = day_start
        latest_start = day_end - timedelta(minutes=duration)
        while cursor <= latest_start:
            slot_start = cursor
            slot_stop = cursor + timedelta(minutes=duration)
            utc_slot_start = slot_start.astimezone(pytz.utc).replace(tzinfo=None)
            utc_slot_stop = slot_stop.astimezone(pytz.utc).replace(tzinfo=None)
            if not self._slot_busy(events, utc_slot_start, utc_slot_stop):
                slots.append({
                    'value': fields.Datetime.to_string(utc_slot_start),
                    'label': slot_start.strftime('%I:%M %p').lstrip('0'),
                })
            cursor += timedelta(minutes=_SLOT_MINUTES)

        return {
            'success': True,
            'slots': slots,
            'message': _('No available times on this day.') if not slots else '',
        }

    @http.route(
        '/quote_manage_ui/appointment/book',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def appointment_book(self, **post):
        env = self._booking_env()
        user_id = int(post.get('user_id') or 0)
        type_id = int(post.get('appointment_type_id') or 0)
        start_raw = (post.get('start') or '').strip()
        name = (post.get('name') or '').strip()
        email = (post.get('email') or '').strip().lower()
        phone = (post.get('phone') or '').strip()

        if not name:
            return {'success': False, 'message': _('Please enter your name.')}
        if not email or not _EMAIL_RE.match(email):
            return {'success': False, 'message': _('Please enter a valid email address.')}

        staff = env['res.users'].browse(user_id).exists()
        apt_type = env['website.appointment.type'].browse(type_id).exists()
        if not staff or not staff.active or staff.share:
            return {'success': False, 'message': _('Please choose a staff member.')}
        if not apt_type or not apt_type.active:
            return {'success': False, 'message': _('Please choose an appointment type.')}

        try:
            start_dt = fields.Datetime.to_datetime(start_raw)
        except (TypeError, ValueError):
            return {'success': False, 'message': _('Please choose a time slot.')}

        stop_dt = start_dt + timedelta(minutes=apt_type.duration_minutes)
        conflict = env['calendar.event'].search_count([
            ('user_id', '=', staff.id),
            ('active', '=', True),
            ('start', '<', stop_dt),
            ('stop', '>', start_dt),
        ])
        if conflict:
            return {
                'success': False,
                'message': _('That time was just booked. Please choose another slot.'),
            }

        partner = env['res.partner'].search([('email', '=ilike', email)], limit=1)
        if partner:
            partner.write({
                'name': name,
                'phone': phone or partner.phone,
            })
        else:
            partner = env['res.partner'].create({
                'name': name,
                'email': email,
                'phone': phone,
            })

        try:
            event = env['calendar.event'].create({
                'name': '%s - %s' % (apt_type.name, name),
                'start': start_dt,
                'stop': stop_dt,
                'user_id': staff.id,
                'partner_ids': [(4, partner.id)],
                'description': _(
                    'Website booking\n'
                    'Type: %(type)s\n'
                    'Guest: %(name)s\n'
                    'Email: %(email)s\n'
                    'Phone: %(phone)s',
                    type=apt_type.name,
                    name=name,
                    email=email,
                    phone=phone or '-',
                ),
                'x_is_website_booking': True,
                'x_booking_email': email,
                'x_appointment_type_id': apt_type.id,
            })
        except Exception:
            _logger.exception('Website appointment booking failed for %s', email)
            return {
                'success': False,
                'message': _('Something went wrong — please try again in a moment.'),
            }

        return {
            'success': True,
            'message': _('Your appointment is confirmed.'),
            'booking_reference': str(event.id),
            'event_id': event.id,
        }

    @http.route(
        '/quote_manage_ui/appointment/cancel',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def appointment_cancel(self, **post):
        env = self._booking_env()
        email = (post.get('email') or '').strip().lower()
        booking_reference = (post.get('booking_reference') or '').strip()

        if not email or not _EMAIL_RE.match(email):
            return {'success': False, 'message': _('Please enter a valid email address.')}
        if not booking_reference.isdigit():
            return {
                'success': False,
                'message': _('Please enter the booking reference number.'),
            }

        event = env['calendar.event'].browse(int(booking_reference)).exists()
        if not event or not event.active or not event.x_is_website_booking:
            return {
                'success': False,
                'message': _('We could not find that booking.'),
            }

        partner_emails = {
            (partner.email or '').strip().lower()
            for partner in event.partner_ids
        }
        stored_email = (event.x_booking_email or '').strip().lower()
        if email not in partner_emails and email != stored_email:
            return {
                'success': False,
                'message': _('The email does not match this booking.'),
            }

        try:
            event.write({'active': False})
        except Exception:
            _logger.exception(
                'Website appointment cancel failed for booking %s',
                booking_reference,
            )
            return {
                'success': False,
                'message': _('Something went wrong — please try again in a moment.'),
            }

        return {
            'success': True,
            'message': _('Your appointment has been cancelled.'),
        }
