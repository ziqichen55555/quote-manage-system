# -*- coding: utf-8 -*-
"""1.0.128 — CMOS attribute from Blancco motherboard test (re-import merge CSV to apply)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.128: attr_cmos added; re-upload MERGED import-ready CSV to populate CMOS on products."
    )
