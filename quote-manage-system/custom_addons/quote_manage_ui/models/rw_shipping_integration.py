# -*- coding: utf-8 -*-
import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

AUSPOST_PAC_BASE = "https://digitalapi.auspost.com.au"
CARTONPILOT_OPTIMIZE_URL = "https://cartonpilot.com/api/v1/shipping-optimize"
GST_FACTOR = 1.1


class RwShippingIntegration(models.AbstractModel):
    _name = "rw.shipping.integration"
    _description = "AusPost PAC + CartonPilot orchestration"

    def _icp(self):
        return self.env["ir.config_parameter"].sudo()

    def pipeline_enabled(self):
        icp = self._icp()
        if icp.get_param("quote_manage_ui.shipping_pipeline_enabled", "False") != "True":
            return False
        if not (icp.get_param("quote_manage_ui.auspost_auth_key") or "").strip():
            return False
        if not (icp.get_param("quote_manage_ui.auspost_from_postcode") or "").strip():
            return False
        return True

    def _packaging_params(self):
        icp = self._icp()

        def _float_param(key, default):
            raw = icp.get_param(key)
            if raw is None or raw == "":
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        return {
            "add_cm": max(0.0, _float_param("quote_manage_ui.shipping_pack_add_cm", 2.0)),
            "extra_kg_per_unit": max(
                0.0, _float_param("quote_manage_ui.shipping_pack_extra_kg", 0.15)
            ),
            "extra_kg_per_parcel": max(
                0.0, _float_param("quote_manage_ui.shipping_pack_parcel_extra_kg", 0.2)
            ),
        }

    def _sorted_dims(self, length, width, height):
        return sorted([float(length), float(width), float(height)])

    def _item_fits_box(self, box, item_l, item_w, item_h):
        box_dims = self._sorted_dims(box.length_cm, box.width_cm, box.height_cm)
        item_dims = self._sorted_dims(item_l, item_w, item_h)
        return (
            item_dims[0] <= box_dims[0]
            and item_dims[1] <= box_dims[1]
            and item_dims[2] <= box_dims[2]
        )

    def _active_auspost_boxes(self):
        return self.env["rw.auspost.parcel.box"].search([("active", "=", True)])

    def _build_items_from_order(self, order):
        """Expand order lines to CartonPilot items (cm, kg)."""
        pack = self._packaging_params()
        pad = pack["add_cm"]
        extra_kg = pack["extra_kg_per_unit"]
        items = []
        missing = []
        for line in order._rw_freight_product_lines():
            product = line.product_id
            tmpl = product.product_tmpl_id
            l_cm = tmpl.rw_ship_length_cm or 0.0
            w_cm = tmpl.rw_ship_width_cm or 0.0
            h_cm = tmpl.rw_ship_height_cm or 0.0
            if l_cm <= 0 or w_cm <= 0 or h_cm <= 0:
                missing.append(product.display_name)
                continue
            l_cm = l_cm + pad
            w_cm = w_cm + pad
            h_cm = h_cm + pad
            weight = product.weight or 0.0
            if weight <= 0:
                weight = 1.0
            weight = weight + extra_kg
            qty = int(math.ceil(line.product_uom_qty))
            items.append(
                {
                    "id": f"line-{line.id}",
                    "dimensions": {
                        "length": l_cm,
                        "width": w_cm,
                        "height": h_cm,
                    },
                    "weight": weight,
                    "quantity": max(1, qty),
                }
            )
        if missing:
            raise UserError(
                _(
                    "Cannot calculate Australia Post shipping: missing pack dimensions "
                    "(L×W×H cm) on: %(products)s",
                    products=", ".join(missing[:8])
                    + ("…" if len(missing) > 8 else ""),
                )
            )
        if not items:
            raise UserError(_("No shippable items to pack."))
        return items

    def _cartonize_cartonpilot(self, items, boxes):
        icp = self._icp()
        api_key = (icp.get_param("quote_manage_ui.cartonpilot_api_key") or "").strip()
        if not api_key:
            return self._cartonize_builtin(items, boxes)

        payload = {
            "boxes": [box._cartonpilot_box_payload() for box in boxes],
            "items": items,
            "options": {"objective": "fewest-parcels"},
        }
        try:
            response = requests.post(
                CARTONPILOT_OPTIMIZE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            _logger.warning("CartonPilot request failed: %s", exc)
            return self._cartonize_builtin(items, boxes)

        if not body.get("success"):
            raise UserError(
                _("CartonPilot could not optimize packing: %(msg)s", msg=body)
            )
        data = body.get("data") or {}
        unpacked = data.get("unpackedItems") or []
        if unpacked:
            raise UserError(
                _(
                    "Some items do not fit available Australia Post box sizes. "
                    "Please contact us for a shipping quote."
                )
            )
        shipments = data.get("shipments") or []
        if not shipments:
            raise UserError(_("CartonPilot returned no shipments."))
        parcels = []
        for shipment in shipments:
            box = shipment.get("box") or {}
            dims = box.get("dimensions") or {}
            length = dims.get("length")
            width = dims.get("width")
            height = dims.get("height")
            if not all([length, width, height]):
                raise UserError(_("CartonPilot shipment missing box dimensions."))
            billing = shipment.get("billing") or {}
            weight = billing.get("billableWeight") or shipment.get("totalWeight")
            if not weight:
                weight = shipment.get("contentsWeight") or 0.0
            weight = float(weight)
            if weight <= 0:
                weight = 0.1
            parcels.append(
                {
                    "length_cm": float(length),
                    "width_cm": float(width),
                    "height_cm": float(height),
                    "weight_kg": weight,
                    "box_id": box.get("id"),
                }
            )
        return parcels

    def _cartonize_builtin(self, items, boxes):
        """Naive fallback: one parcel per line quantity unit (smallest fitting box)."""
        _logger.info("Using built-in cartonization fallback (no or failed CartonPilot).")
        if not boxes:
            raise UserError(_("No Australia Post box sizes configured."))
        boxes_sorted = boxes.sorted(
            key=lambda b: b.length_cm * b.width_cm * b.height_cm
        )
        parcels = []
        for item in items:
            dims = item["dimensions"]
            qty = int(item.get("quantity") or 1)
            unit_weight = float(item.get("weight") or 1.0)
            for _index in range(qty):
                fitted = None
                for box in boxes_sorted:
                    if self._item_fits_box(
                        box, dims["length"], dims["width"], dims["height"]
                    ):
                        fitted = box
                        break
                if not fitted:
                    raise UserError(
                        _(
                            "Item %(item)s does not fit any configured Australia Post box.",
                            item=item.get("id"),
                        )
                    )
                parcels.append(
                    {
                        "length_cm": fitted.length_cm,
                        "width_cm": fitted.width_cm,
                        "height_cm": fitted.height_cm,
                        "weight_kg": min(unit_weight, fitted.max_weight_kg),
                        "box_id": fitted.auspost_code,
                    }
                )
        return self._merge_parcels_heuristic(parcels, boxes)

    def _merge_parcels_heuristic(self, parcels, boxes):
        """Try to merge single-item parcels into one box when volume/weight allow."""
        if len(parcels) <= 1:
            return parcels
        boxes_by_vol = boxes.sorted(
            key=lambda b: b.length_cm * b.width_cm * b.height_cm
        )
        total_weight = sum(p["weight_kg"] for p in parcels)
        max_l = max(p["length_cm"] for p in parcels)
        max_w = max(p["width_cm"] for p in parcels)
        max_h = max(p["height_cm"] for p in parcels)
        total_vol = sum(
            p["length_cm"] * p["width_cm"] * p["height_cm"] for p in parcels
        )
        for box in boxes_by_vol:
            if total_weight > box.max_weight_kg:
                continue
            if not self._item_fits_box(box, max_l, max_w, max_h):
                continue
            box_vol = box.length_cm * box.width_cm * box.height_cm
            if total_vol <= box_vol * 0.9:
                return [
                    {
                        "length_cm": box.length_cm,
                        "width_cm": box.width_cm,
                        "height_cm": box.height_cm,
                        "weight_kg": total_weight,
                        "box_id": box.auspost_code,
                    }
                ]
        return parcels

    def _pac_get_json(self, path, params, api_key):
        query = urllib.parse.urlencode(params)
        url = f"{AUSPOST_PAC_BASE}{path}?{query}"
        req = urllib.request.Request(
            url,
            headers={"AUTH-KEY": api_key, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            _logger.warning("AusPost PAC HTTP %s: %s", exc.code, body)
            raise UserError(
                _("Australia Post postage API error (%(code)s).", code=exc.code)
            ) from exc
        except urllib.error.URLError as exc:
            raise UserError(_("Could not reach Australia Post API.")) from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UserError(_("Invalid response from Australia Post API.")) from exc

    def _pac_parcel_cost_inc_gst(self, from_pc, to_pc, parcel, service_code, api_key):
        params = {
            "from_postcode": from_pc,
            "to_postcode": to_pc,
            "length": parcel["length_cm"],
            "width": parcel["width_cm"],
            "height": parcel["height_cm"],
            "weight": parcel["weight_kg"],
            "service_code": service_code,
        }
        data = self._pac_get_json(
            "/postage/parcel/domestic/calculate.json", params, api_key
        )
        result = data.get("postage_result") or {}
        if not result:
            raise UserError(_("Australia Post returned no postage result."))
        total = result.get("total_cost")
        if total is None:
            costs = result.get("costs") or {}
            cost = costs.get("cost")
            if isinstance(cost, list):
                total = sum(float(c.get("cost", 0) or 0) for c in cost)
            elif isinstance(cost, dict):
                total = cost.get("cost")
        if total is None:
            raise UserError(_("Australia Post response missing total cost."))
        return float(total)

    def quote_order_freight_ex_gst(self, order):
        """Pack order lines → CartonPilot/builtin → sum AusPost PAC (ex GST)."""
        order.ensure_one()
        icp = self._icp()
        api_key = (icp.get_param("quote_manage_ui.auspost_auth_key") or "").strip()
        from_pc = (icp.get_param("quote_manage_ui.auspost_from_postcode") or "").strip()
        service_code = (
            icp.get_param("quote_manage_ui.auspost_service_code") or "AUS_PARCEL_REGULAR"
        ).strip()
        to_partner = order.partner_shipping_id
        if not to_partner or to_partner.country_id.code != "AU":
            raise UserError(_("Australia Post rates require an Australian shipping address."))
        to_pc = (to_partner.zip or "").strip().replace(" ", "")[:4]
        if not to_pc or not to_pc.isdigit():
            raise UserError(_("Shipping postcode is missing or invalid."))

        boxes = self._active_auspost_boxes()
        items = self._build_items_from_order(order)
        parcels = self._cartonize_cartonpilot(items, boxes)
        parcel_extra = self._packaging_params()["extra_kg_per_parcel"]
        if parcel_extra:
            for parcel in parcels:
                parcel["weight_kg"] = float(parcel.get("weight_kg") or 0.1) + parcel_extra

        total_inc_gst = 0.0
        for parcel in parcels:
            total_inc_gst += self._pac_parcel_cost_inc_gst(
                from_pc, to_pc, parcel, service_code, api_key
            )
        return round(total_inc_gst / GST_FACTOR, 2)
