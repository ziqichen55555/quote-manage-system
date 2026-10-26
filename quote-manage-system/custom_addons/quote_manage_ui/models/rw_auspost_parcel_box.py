# -*- coding: utf-8 -*-
from odoo import fields, models


class RwAuspostParcelBox(models.Model):
    _name = "rw.auspost.parcel.box"
    _description = "Australia Post standard parcel box (carton catalog)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    auspost_code = fields.Char(
        string="AusPost type code",
        help="Code from Australia Post PAC parcel size API (e.g. AUS_PARCEL_TYPE_BOXED_BM).",
    )
    length_cm = fields.Float(string="Length (cm)", required=True, digits=(16, 2))
    width_cm = fields.Float(string="Width (cm)", required=True, digits=(16, 2))
    height_cm = fields.Float(string="Height (cm)", required=True, digits=(16, 2))
    max_weight_kg = fields.Float(
        string="Max weight (kg)",
        default=22.0,
        help="Maximum total parcel weight allowed for this box type.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _cartonpilot_box_payload(self):
        self.ensure_one()
        return {
            "id": self.auspost_code or f"rw-box-{self.id}",
            "dimensions": {
                "length": self.length_cm,
                "width": self.width_cm,
                "height": self.height_cm,
            },
            "weightCapacity": self.max_weight_kg,
        }
