# -*- coding: utf-8 -*-
"""Public appointment booking page — create / cancel calendar.event records."""

import logging
import re
import time
from datetime import datetime, time as dt_time, timedelta

import pytz

from odoo import _, fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_WORK_START_HOUR = 9
_WORK_END_HOUR = 17
_SLOT_MINUTES = 30
_BOOKING_HORIZON_DAYS = 30
_MIN_SUBMIT_SECONDS = 3
_MAX_BOOKINGS_PER_EMAIL_HOUR = 5


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

    def _get_calendar_user(self, env):
        return env['res.config.settings'].get_appointment_calendar_user()

    def _get_team_users(self, env):
        return env['res.config.settings'].get_appointment_team_users()

    def _team_busy_events(self, env, utc_start, utc_end):
        team_users = self._get_team_users(env)
        if not team_users:
            return env['calendar.event']
        team_partners = team_users.partner_id.ids
        return env['calendar.event'].search([
            ('active', '=', True),
            ('start', '<', utc_end),
            ('stop', '>', utc_start),
            '|',
            ('user_id', 'in', team_users.ids),
            ('partner_ids', 'in', team_partners),
        ])

    def _booking_guest_partner_ids(self, guest_partner):
        """Guest only — organizer is not listed as an invitee."""
        if guest_partner:
            return [guest_partner.id]
        return []

    def _send_booking_confirmation_email(
        self, env, event, email, name, slot_labels, booking_reference,
    ):
        company = env.company
        from_addr = company.email or 're-ware@cocreativeit.com'
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        cancel_url = '%s/book-appointment' % base_url.rstrip('/')
        body = _(
            '<p>Hi %(name)s,</p>'
            '<p>Your appointment is confirmed.</p>'
            '<p><strong>Booking reference:</strong> %(reference)s<br/>'
            '<strong>When:</strong> %(date)s at %(time)s<br/>'
            '<strong>Type:</strong> %(type)s</p>'
            '<p>About 30 minutes before your appointment, everyone on the team '
            'and you will receive a calendar invite by email.</p>'
            '<p>To cancel, go to '
            '<a href="%(cancel_url)s">%(cancel_url)s</a> and enter the same '
            'email plus your booking reference.</p>'
            '<p>Re-Ware</p>',
            name=name,
            reference=booking_reference,
            date=slot_labels['date_label'],
            time=slot_labels['time_label'],
            type=slot_labels['type_name'],
            cancel_url=cancel_url,
        )
        try:
            mail = env['mail.mail'].sudo().create({
                'email_from': from_addr,
                'email_to': email,
                'subject': _('Appointment confirmed — reference %(ref)s', ref=booking_reference),
                'body_html': body,
                'auto_delete': True,
            })
            mail.send()
            return True
        except Exception:
            _logger.exception(
                'Booking confirmation email failed for reference %s',
                booking_reference,
            )
            return False

    def _localize_slot(self, tz, day, hour, minute):
        naive = datetime.combine(day, dt_time(hour, minute))
        return tz.localize(naive)

    def _bot_rejection(self, post):
        """Lightweight anti-bot checks — no Cloudflare required."""
        if (post.get('company') or '').strip():
            return _('Invalid submission.')
        loaded_at = post.get('form_loaded_at')
        if loaded_at:
            try:
                if time.time() - float(loaded_at) < _MIN_SUBMIT_SECONDS:
                    return _('Please wait a moment before submitting.')
            except (TypeError, ValueError):
                return _('Invalid submission.')
        else:
            return _('Invalid submission.')
        return None

    def _booking_rate_limited(self, env, email):
        since = fields.Datetime.now() - timedelta(hours=1)
        count = env['calendar.event'].search_count([
            ('x_is_website_booking', '=', True),
            ('x_booking_email', '=ilike', email),
            ('create_date', '>=', since),
        ])
        return count >= _MAX_BOOKINGS_PER_EMAIL_HOUR

    def _slot_busy(self, events, slot_start, slot_stop):
        for event in events:
            if event.allday:
                return True
            if event.start < slot_stop and event.stop > slot_start:
                return True
        return False

    def _format_booking_slot(self, tz, start_dt, apt_type):
        start_local = pytz.utc.localize(start_dt).astimezone(tz)
        return {
            'date_label': start_local.strftime('%a, %d %b %Y'),
            'time_label': start_local.strftime('%I:%M %p').lstrip('0'),
            'type_name': apt_type.name,
        }

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
        calendar_user = self._get_calendar_user(env)
        if not types:
            return {
                'success': False,
                'message': _('No appointment types are configured yet.'),
            }
        if not calendar_user:
            return {
                'success': False,
                'message': _('No calendar is configured for website bookings yet.'),
            }
        tz = self._booking_tz(env)
        dates = self._serialize_dates(tz)
        return {
            'success': True,
            'types': self._serialize_types(types),
            'dates': dates,
            'default_date': dates[0]['value'] if dates else '',
            'default_type_id': types[0].id if types else False,
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
        date_str = (post.get('date') or '').strip()
        type_id = int(post.get('appointment_type_id') or 0)

        apt_type = env['website.appointment.type'].browse(type_id).exists()
        if not apt_type or not apt_type.active:
            return {'success': False, 'message': _('Please choose an appointment type.')}
        if not self._get_calendar_user(env):
            return {
                'success': False,
                'message': _('No calendar is configured for website bookings yet.'),
            }

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

        calendar_user = self._get_calendar_user(env)
        events = self._team_busy_events(env, utc_start, utc_end)

        now_utc = fields.Datetime.now()
        slots = []
        default_slot = ''
        cursor = day_start
        latest_start = day_end - timedelta(minutes=duration)
        while cursor <= latest_start:
            slot_start = cursor
            slot_stop = cursor + timedelta(minutes=duration)
            utc_slot_start = slot_start.astimezone(pytz.utc).replace(tzinfo=None)
            utc_slot_stop = slot_stop.astimezone(pytz.utc).replace(tzinfo=None)
            if day == today and utc_slot_start < now_utc:
                cursor += timedelta(minutes=_SLOT_MINUTES)
                continue
            if not self._slot_busy(events, utc_slot_start, utc_slot_stop):
                slot_value = fields.Datetime.to_string(utc_slot_start)
                slots.append({
                    'value': slot_value,
                    'label': slot_start.strftime('%I:%M %p').lstrip('0'),
                })
                if not default_slot:
                    default_slot = slot_value
            cursor += timedelta(minutes=_SLOT_MINUTES)

        return {
            'success': True,
            'slots': slots,
            'default_slot': default_slot,
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
        bot_error = self._bot_rejection(post)
        if bot_error:
            return {'success': False, 'message': bot_error}

        type_id = int(post.get('appointment_type_id') or 0)
        start_raw = (post.get('start') or '').strip()
        name = (post.get('name') or '').strip()
        email = (post.get('email') or '').strip().lower()
        phone = (post.get('phone') or '').strip()

        if not name:
            return {'success': False, 'message': _('Please enter your name.')}
        if not email:
            return {
                'success': False,
                'message': _('Please enter your email — you need it to cancel later.'),
            }
        if not _EMAIL_RE.match(email):
            return {'success': False, 'message': _('Please enter a valid email address.')}

        if email and self._booking_rate_limited(env, email):
            return {
                'success': False,
                'message': _('Too many booking attempts. Please try again later.'),
            }

        calendar_user = self._get_calendar_user(env)
        apt_type = env['website.appointment.type'].browse(type_id).exists()
        if not calendar_user:
            return {
                'success': False,
                'message': _('No calendar is configured for website bookings yet.'),
            }
        if not apt_type or not apt_type.active:
            return {'success': False, 'message': _('Please choose an appointment type.')}

        try:
            start_dt = fields.Datetime.to_datetime(start_raw)
        except (TypeError, ValueError):
            return {'success': False, 'message': _('Please choose a time slot.')}

        if start_dt < fields.Datetime.now():
            return {'success': False, 'message': _('Please choose a future time slot.')}

        stop_dt = start_dt + timedelta(minutes=apt_type.duration_minutes)
        conflict = self._team_busy_events(env, start_dt, stop_dt)
        if conflict:
            return {
                'success': False,
                'message': _('That time was just booked. Please choose another slot.'),
            }

        partner = False
        if email:
            partner = env['res.partner'].search([('email', '=ilike', email)], limit=1)
        if partner:
            partner.write({
                'name': name,
                'phone': phone or partner.phone,
            })
        else:
            partner_vals = {'name': name}
            if email:
                partner_vals['email'] = email
            if phone:
                partner_vals['phone'] = phone
            partner = env['res.partner'].create(partner_vals)

        guest_partner_ids = self._booking_guest_partner_ids(partner)
        company = calendar_user.company_id
        location = env['calendar.event']._format_company_address(company)
        create_vals = {
                'name': '%s - %s' % (apt_type.name, name),
                'start': start_dt,
                'stop': stop_dt,
                'user_id': calendar_user.id,
                'location': location,
                'description': _(
                    'Website booking\n'
                    'Type: %(type)s\n'
                    'Guest: %(name)s\n'
                    'Email: %(email)s\n'
                    'Phone: %(phone)s',
                    type=apt_type.name,
                    name=name,
                    email=email or '-',
                    phone=phone or '-',
                ),
                'x_is_website_booking': True,
                'x_booking_email': email or False,
                'x_appointment_type_id': apt_type.id,
                'x_booking_invite_sent': False,
        }
        if guest_partner_ids:
            create_vals['partner_ids'] = [(6, 0, guest_partner_ids)]

        try:
            event = env['calendar.event'].with_user(calendar_user).with_context(
                no_mail_to_attendees=True,
                dont_notify=True,
                mail_create_nolog=True,
            ).create(create_vals)
        except Exception:
            _logger.exception('Website appointment booking failed for %s', email)
            return {
                'success': False,
                'message': _('Something went wrong — please try again in a moment.'),
            }

        slot_labels = self._format_booking_slot(
            self._booking_tz(env), start_dt, apt_type,
        )
        booking_reference = str(event.id)
        email_sent = self._send_booking_confirmation_email(
            env, event, email, name, slot_labels, booking_reference,
        )
        return {
            'success': True,
            'message': _('Your appointment is confirmed.'),
            'booking_reference': booking_reference,
            'event_id': event.id,
            'appointment_type': slot_labels['type_name'],
            'date_label': slot_labels['date_label'],
            'time_label': slot_labels['time_label'],
            'guest_name': name,
            'guest_email': email,
            'confirmation_email_sent': email_sent,
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
        bot_error = self._bot_rejection(post)
        if bot_error:
            return {'success': False, 'message': bot_error}

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
