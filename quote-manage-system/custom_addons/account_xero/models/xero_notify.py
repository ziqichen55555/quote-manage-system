# -*- coding: utf-8 -*-

from odoo import _


def xero_client_notification(title, message, notification_type='success', sticky=False):
    """Return an Odoo web client toast action."""
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': title,
            'message': message,
            'type': notification_type,
            'sticky': sticky or notification_type in ('danger', 'warning'),
        },
    }


def xero_short_api_error(message):
    """Trim long Xero JSON errors for UI display."""
    text = message or ''
    if 'ValidationErrors' in text and 'Message' in text:
        for needle in ('Account could not be found', 'Contact name must be unique'):
            if needle in text:
                return needle
    if len(text) > 280:
        return text[:280] + '…'
    return text
