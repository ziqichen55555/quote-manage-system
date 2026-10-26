# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    rw_ship_length_cm = fields.Float(
        string="Pack length (cm)",
        digits=(16, 2),
        help="Outer shipping length in centimetres (single unit) for cartonization.",
    )
    rw_ship_width_cm = fields.Float(
        string="Pack width (cm)",
        digits=(16, 2),
    )
    rw_ship_height_cm = fields.Float(
        string="Pack height (cm)",
        digits=(16, 2),
    )
