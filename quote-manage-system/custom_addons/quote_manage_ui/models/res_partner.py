# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        res = super().write(vals)
        if "zip" in vals:
            orders = self.env["sale.order"].sudo().search(
                [
                    ("website_id", "!=", False),
                    ("state", "=", "draft"),
                    ("partner_shipping_id", "in", self.ids),
                ]
            )
            orders._rw_ensure_default_freight()
        return res
