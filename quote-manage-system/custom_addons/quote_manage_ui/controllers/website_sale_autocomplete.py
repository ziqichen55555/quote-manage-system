# -*- coding: utf-8 -*-
"""Places API (New) for checkout address — Legacy Places is disabled on many GCP projects."""

import logging
import re

import requests

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.website_sale_autocomplete.controllers.main import (
    FIELDS_PRIORITY,
    TIMEOUT,
    AutoCompleteController,
)

_logger = logging.getLogger(__name__)

PLACES_NEW_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
PLACES_NEW_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"


class RewareAutoCompleteController(AutoCompleteController):
    @http.route("/autocomplete/address", methods=["POST"], type="json", auth="public", website=True)
    def _autocomplete_address(self, partial_address, session_id=None, country_id=None):
        api_key = request.env["website"].get_current_website().sudo().google_places_api_key
        country_code = self._rw_places_country_code(country_id)
        return self._perform_place_search(
            partial_address,
            session_id=session_id,
            api_key=api_key,
            country_code=country_code,
        )

    @http.route("/autocomplete/address_full", methods=["POST"], type="json", auth="public", website=True)
    def _autocomplete_address_full(self, address, session_id=None, google_place_id=None, **kwargs):
        api_key = request.env["website"].get_current_website().sudo().google_places_api_key
        out = self._perform_complete_place_search(
            address,
            google_place_id=google_place_id,
            session_id=session_id,
            api_key=api_key,
            **kwargs,
        )
        if isinstance(out, dict):
            out.setdefault(
                "rw_debug",
                {
                    "step": "address_full",
                    "api": "places_new",
                    "has_api_key": bool(api_key and str(api_key).strip()),
                    "place_id": google_place_id,
                    "filled": bool(out.get("city") or out.get("zip")),
                },
            )
        return out

    def _perform_place_search(
        self,
        partial_address,
        api_key=None,
        session_id=None,
        language_code=None,
        country_code=None,
    ):
        rw_debug = {
            "step": "autocomplete",
            "api": "places_new",
            "partial_len": len(partial_address or ""),
            "has_api_key": bool(api_key and str(api_key).strip()),
            "key_prefix": str(api_key)[:8] if api_key else None,
            "country_code": country_code,
        }
        min_len = 3
        if len(partial_address or "") < min_len:
            rw_debug["skip"] = f"type at least {min_len} characters in Street (you had {len(partial_address or '')})"
            return {"results": [], "session_id": session_id, "rw_debug": rw_debug}

        if not api_key:
            rw_debug["google_status"] = "MISSING_API_KEY"
            rw_debug["google_error"] = "website.google_places_api_key is empty in Odoo"
            return {"results": [], "session_id": session_id, "rw_debug": rw_debug}

        region = (country_code or "au").upper()
        body = {
            "input": partial_address,
            "includedRegionCodes": [region],
            "regionCode": region.lower(),
        }
        if session_id:
            body["sessionToken"] = session_id
        if language_code:
            body["languageCode"] = language_code

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "suggestions.placePrediction.placeId,"
                "suggestions.placePrediction.text,"
                "suggestions.placePrediction.structuredFormat"
            ),
        }

        try:
            response = requests.post(
                PLACES_NEW_AUTOCOMPLETE_URL,
                json=body,
                headers=headers,
                timeout=TIMEOUT,
            )
            payload = response.json()
        except (TimeoutError, ValueError, requests.RequestException) as exc:
            _logger.error("Places (New) autocomplete failed: %s", exc)
            rw_debug["google_status"] = "REQUEST_FAILED"
            rw_debug["google_error"] = str(exc)[:300]
            return {"results": [], "session_id": session_id, "rw_debug": rw_debug}

        if payload.get("error"):
            err = payload["error"]
            rw_debug["google_status"] = err.get("status", "ERROR")
            rw_debug["google_error"] = err.get("message")
            _logger.error("Places (New) autocomplete: %s", rw_debug["google_error"])
            return {"results": [], "session_id": session_id, "rw_debug": rw_debug}

        rw_debug["google_status"] = "OK"
        results = []
        for suggestion in payload.get("suggestions") or []:
            prediction = suggestion.get("placePrediction")
            if not prediction:
                continue
            place_id = prediction.get("placeId")
            text = (prediction.get("text") or {}).get("text")
            if not text:
                structured = prediction.get("structuredFormat") or {}
                main = (structured.get("mainText") or {}).get("text") or ""
                secondary = (structured.get("secondaryText") or {}).get("text") or ""
                text = ", ".join(part for part in (main, secondary) if part)
            if place_id and text:
                results.append(
                    {
                        "formatted_address": text,
                        "google_place_id": place_id,
                    }
                )

        rw_debug["predictions_count"] = len(results)
        return {
            "results": results,
            "session_id": session_id,
            "rw_debug": rw_debug,
        }

    def _perform_complete_place_search(
        self,
        address,
        api_key=None,
        google_place_id=None,
        language_code=None,
        session_id=None,
    ):
        if not api_key or not google_place_id:
            return {}

        place_id = requests.utils.quote(str(google_place_id), safe="")
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "addressComponents,formattedAddress,adrFormatAddress",
        }
        params = {}
        if session_id:
            params["sessionToken"] = session_id
        if language_code:
            params["languageCode"] = language_code

        try:
            response = requests.get(
                PLACES_NEW_DETAILS_URL.format(place_id=place_id),
                headers=headers,
                params=params or None,
                timeout=TIMEOUT,
            )
            payload = response.json()
        except (TimeoutError, ValueError, requests.RequestException) as exc:
            _logger.error("Places (New) details failed: %s", exc)
            return {}

        if payload.get("error"):
            _logger.error("Places (New) details: %s", payload["error"].get("message"))
            return {}

        formatted_address = payload.get("formattedAddress") or address
        adr_format = payload.get("adrFormatAddress") or formatted_address
        components = self._rw_new_components_to_legacy(payload.get("addressComponents") or [])

        components.sort(
            key=lambda r: FIELDS_PRIORITY.index(r["type"]) if r["type"] in FIELDS_PRIORITY else 100
        )
        standard_address = self._translate_google_to_standard(components)

        if "number" not in standard_address:
            standard_address["number"] = self._guess_number_from_input(address, standard_address)
            standard_address["formatted_street_number"] = (
                f'{standard_address["number"]} {standard_address.get("street", "")}'
            )
        else:
            formatted_from_html = html2plaintext(re.split(r"[,<]", adr_format)[0])
            formatted_manually = f'{standard_address["number"]} {standard_address.get("street", "")}'
            if len(formatted_from_html) >= len(formatted_manually):
                standard_address["formatted_street_number"] = formatted_from_html
            else:
                standard_address["formatted_street_number"] = formatted_manually

        self._rw_apply_unit_street2(
            standard_address,
            payload.get("addressComponents") or [],
            address,
            formatted_address,
        )
        return standard_address

    def _rw_apply_unit_street2(self, standard_address, new_components, source_label, formatted_address):
        """Map unit/subpremise to street2 (AU 1/172 … → Unit 1 + street without prefix)."""
        street2 = self._rw_subpremise_from_components(new_components)
        if not street2:
            unit = self._rw_au_unit_token_from_text(source_label) or self._rw_au_unit_token_from_text(
                formatted_address
            )
            if unit:
                street2 = f"Unit {unit}"

        if street2:
            standard_address["street2"] = street2

        for key in ("formatted_street_number",):
            value = standard_address.get(key)
            if not value:
                continue
            stripped = self._rw_strip_au_unit_prefix(value)
            if stripped:
                standard_address[key] = stripped

    def _rw_subpremise_from_components(self, new_components):
        for comp in new_components:
            types = comp.get("types") or []
            if "subpremise" not in types:
                continue
            val = (comp.get("longText") or comp.get("shortText") or "").strip()
            if val:
                return f"Unit {val}" if re.fullmatch(r"\d+[A-Za-z]?", val) else val
        return None

    def _rw_au_unit_token_from_text(self, text):
        if not text:
            return None
        head = re.split(r"[,]", text, maxsplit=1)[0]
        match = re.match(r"^\s*(?:Unit\s+)?(\d+[A-Za-z]?)\s*/\s*", head, flags=re.I)
        return match.group(1) if match else None

    def _rw_strip_au_unit_prefix(self, line):
        match = re.match(r"^\s*(?:Unit\s+)?\d+[A-Za-z]?\s*/\s*(.+)$", line.strip(), flags=re.I)
        return match.group(1).strip() if match else None

    def _rw_new_components_to_legacy(self, components):
        legacy = []
        for comp in components:
            types = comp.get("types") or []
            if not types:
                continue
            legacy.append(
                {
                    "long_name": comp.get("longText") or "",
                    "short_name": comp.get("shortText") or "",
                    "type": types[0],
                }
            )
        return legacy

    def _rw_places_country_code(self, country_id):
        if country_id:
            try:
                country = request.env["res.country"].sudo().browse(int(country_id))
                if country.exists():
                    return country.code.lower()
            except (TypeError, ValueError):
                pass
        return "au"
