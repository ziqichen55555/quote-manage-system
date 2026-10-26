# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rw_shipping_pipeline_enabled = fields.Boolean(
        string="Use AusPost + cartonization for website freight",
        config_parameter="quote_manage_ui.shipping_pipeline_enabled",
        help="When enabled and API keys are set, checkout freight uses "
        "CartonPilot (or built-in fallback) and Australia Post PAC instead of $/kg.",
    )
    rw_auspost_auth_key = fields.Char(
        string="Australia Post PAC AUTH-KEY",
        config_parameter="quote_manage_ui.auspost_auth_key",
    )
    rw_cartonpilot_api_key = fields.Char(
        string="CartonPilot API key",
        config_parameter="quote_manage_ui.cartonpilot_api_key",
    )
    rw_auspost_from_postcode = fields.Char(
        string="Ship-from postcode",
        config_parameter="quote_manage_ui.auspost_from_postcode",
    )
    rw_auspost_service_code = fields.Char(
        string="AusPost service code",
        config_parameter="quote_manage_ui.auspost_service_code",
        default="AUS_PARCEL_REGULAR",
    )
    rw_shipping_pack_add_cm = fields.Float(
        string="Pack padding (cm per dimension)",
        config_parameter="quote_manage_ui.shipping_pack_add_cm",
        default=2.0,
        help="Added to each product pack length, width and height before "
        "cartonization (room for foam/bubble wrap). Product master can stay at bare item size.",
    )
    rw_shipping_pack_extra_kg = fields.Float(
        string="Extra weight per unit (kg)",
        config_parameter="quote_manage_ui.shipping_pack_extra_kg",
        default=0.15,
        help="Added to each shippable unit weight (packaging material estimate).",
    )
    rw_shipping_pack_parcel_extra_kg = fields.Float(
        string="Extra weight per parcel (kg)",
        config_parameter="quote_manage_ui.shipping_pack_parcel_extra_kg",
        default=0.2,
        help="Added once per AusPost parcel after packing (empty box / void fill).",
    )
    rw_shipping_markup_percent = fields.Float(
        string="Freight markup (%)",
        config_parameter="quote_manage_ui.shipping_markup_percent",
        default=0.0,
        help="Percentage added to website delivery (ex GST) for orders at/above PAC min kg only. "
        "Under 1 kg uses flat minimum freight with no markup.",
    )
    rw_shipping_markup_fixed_ex_gst = fields.Float(
        string="Freight markup fixed (AUD ex GST)",
        config_parameter="quote_manage_ui.shipping_markup_fixed_ex_gst",
        default=0.0,
        help="Flat amount added to each delivery quote (ex GST), after percent markup.",
    )
