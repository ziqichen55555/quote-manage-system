# -*- coding: utf-8 -*-
"""1.0.129 — Skip restocking serials already delivered to customers on merge import."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.129: merge import no longer restocks serials with done customer deliveries."
    )
