# -*- coding: utf-8 -*-
"""Re-Ware "Follow our journey" newsletter signup endpoint.

Lightweight wrapper that the public snippet form posts to. We deliberately
do not depend on a pre-configured ``mailing.list`` so the front-end keeps
working out of the box: anything the user submits goes onto a single
"Re-Ware Newsletter" list (auto-created on first submit).
"""

import logging
import re

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_LIST_NAME = 'Re-Ware Newsletter'


class RewareNewsletterController(http.Controller):

    @http.route(
        '/quote_manage_ui/newsletter/subscribe',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def reware_newsletter_subscribe(self, **post):
        """Subscribe ``email`` (+ optional first / last name) to the
        Re-Ware mailing list. Returns ``{success, message}``.

        Front-end displays ``message`` verbatim, so keep it user-facing.
        """
        first_name = (post.get('first_name') or '').strip()
        last_name = (post.get('last_name') or '').strip()
        email = (post.get('email') or '').strip().lower()

        if not email or not _EMAIL_RE.match(email):
            return {
                'success': False,
                'message': _("Please enter a valid email address."),
            }

        env = request.env(su=True)
        try:
            mailing_list = env['mailing.list'].search(
                [('name', '=', _LIST_NAME)], limit=1
            )
            if not mailing_list:
                mailing_list = env['mailing.list'].create({
                    'name': _LIST_NAME,
                    'is_public': True,
                })

            existing = env['mailing.contact'].search(
                [('email', '=', email)], limit=1
            )
            display_name = ' '.join(part for part in (first_name, last_name) if part) or email

            if existing:
                if mailing_list.id not in existing.list_ids.ids:
                    existing.write({
                        'list_ids': [(4, mailing_list.id)],
                        'name': existing.name or display_name,
                    })
                    return {
                        'success': True,
                        'message': _("Thanks! You're on the list."),
                    }
                return {
                    'success': True,
                    'message': _("You're already subscribed — thanks for being part of the change!"),
                }

            env['mailing.contact'].create({
                'name': display_name,
                'email': email,
                'list_ids': [(6, 0, [mailing_list.id])],
            })
        except Exception:
            _logger.exception("Re-Ware newsletter subscribe failed for %s", email)
            return {
                'success': False,
                'message': _("Something went wrong on our side — please try again in a moment."),
            }

        return {
            'success': True,
            'message': _("Thanks! You're on the list."),
        }
