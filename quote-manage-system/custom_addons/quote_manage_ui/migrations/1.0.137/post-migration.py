# -*- coding: utf-8 -*-
"""1.0.137 — Hide orphan Series filter values; normalize Series + Generation."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]

    cmos = env.ref("quote_manage_ui.attr_cmos", raise_if_not_found=False)
    if cmos and cmos.visibility != "hidden":
        cmos.write({"visibility": "hidden"})

    fixed_series, fixed_gen = Importer.repair_shop_sidebar_filters()
    _logger.info(
        "1.0.137: Series normalized on %s product(s); Generation backfilled on %s. "
        "Shop sidebar now hides unused attribute values.",
        fixed_series,
        fixed_gen,
    )
