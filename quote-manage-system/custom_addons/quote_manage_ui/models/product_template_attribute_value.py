# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _rw_sync_cmos_shop_on_templates(self):
        attr = self.env["product.template"]._rw_cmos_attr()
        if not attr:
            return
        self.filtered(lambda v: v.attribute_id == attr).mapped(
            "product_tmpl_id"
        )._rw_sync_shop_from_cmos()

    def write(self, vals):
        res = super().write(vals)
        if "product_attribute_value_id" in vals or "name" in vals:
            self._rw_sync_cmos_shop_on_templates()
        return res

    def create(self, vals_list):
        ptavs = super().create(vals_list)
        ptavs._rw_sync_cmos_shop_on_templates()
        return ptavs
