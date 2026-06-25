# -*- coding: utf-8 -*-
"""1.0.121: battery-tier SKUs inherit list_price from base MTM when CSV Price is empty."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE product_template bt
        SET list_price = base.list_price
        FROM product_template base
        WHERE bt.list_price = 0
          AND base.list_price > 0
          AND (
            bt.default_code LIKE '%-BT70'
            OR bt.default_code LIKE '%-BTU70'
          )
          AND base.default_code = regexp_replace(
            bt.default_code, '-(BT70|BTU70)$', ''
          )
          AND base.id <> bt.id
        """
    )
