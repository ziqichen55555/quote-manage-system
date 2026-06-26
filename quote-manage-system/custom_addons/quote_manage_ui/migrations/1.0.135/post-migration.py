# -*- coding: utf-8 -*-
"""1.0.135 — CMOSFL→Successful moves serial stock to CMOSP shop master (one listing)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.135: approving CMOS on -CMOSFL buckets transfers stock to -CMOSP for the shop."
    )
