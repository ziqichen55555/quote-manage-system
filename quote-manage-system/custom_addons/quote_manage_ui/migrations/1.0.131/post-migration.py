# -*- coding: utf-8 -*-
"""1.0.131 — No CMOS: stock in WH/Stock but website_published/sale_ok False until manual publish."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "1.0.131: merge import holds products without CMOS off the shop (scheme A)."
    )
