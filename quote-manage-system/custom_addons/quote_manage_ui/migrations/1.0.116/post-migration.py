# -*- coding: utf-8 -*-
"""1.0.116 — Split lot-less quants on serial-tracked laptops/desktops (delivery SN dropdown)."""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"].sudo()
    if hasattr(Importer, "consolidate_legacy_rw_skus"):
        Importer.consolidate_legacy_rw_skus()
    if hasattr(Importer, "repair_serial_stock_quants"):
        result = Importer.repair_serial_stock_quants()
        _logger.info("repair_serial_stock_quants: %s", result)
