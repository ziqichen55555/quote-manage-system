# -*- coding: utf-8 -*-
"""1.0.120 — Battery attribute + 70% tier shop SKUs (re-import merge CSV to apply)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.120: attr_battery added; upload MERGED import-ready CSV to split laptop SKUs by BT70/BTU70."
    )
