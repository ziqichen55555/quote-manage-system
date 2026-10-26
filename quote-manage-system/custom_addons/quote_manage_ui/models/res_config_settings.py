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
