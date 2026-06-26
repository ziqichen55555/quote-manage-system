# -*- coding: utf-8 -*-
"""1.0.134 — Manual CMOS attribute edit auto-syncs website_published / sale_ok."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.134: changing CMOS to Successful on a product now publishes it to the shop."
    )
