# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def post_init_hook(env):
    """Bootstrap a disabled Airwallex provider for every existing company.

    The XML data file seeds a single company-less template; this hook
    fans it out so multi-company tenants don't have to manually clone
    the row before configuring credentials.
    """
    env['payment.provider']._setup_provider('airwallex')


def uninstall_hook(env):
    """Mirror of ``post_init_hook`` -- removes the Airwallex provider rows."""
    env['payment.provider']._remove_provider('airwallex')
