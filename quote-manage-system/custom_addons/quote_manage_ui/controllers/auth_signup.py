# -*- coding: utf-8 -*-
"""Require phone + address when creating a portal account for website quotes."""
from odoo import _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request


_CONTACT_SIGNUP_KEYS = (
    "phone",
    "street",
    "street2",
    "city",
    "zip",
    "country_id",
    "state_id",
)


class RewareAuthSignupHome(AuthSignupHome):
    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        for key in _CONTACT_SIGNUP_KEYS:
            if key in request.params and key not in qcontext:
                qcontext[key] = request.params.get(key)
        # Countries for the signup address form.
        qcontext.setdefault(
            "countries",
            request.env["res.country"].sudo().search([]),
        )
        qcontext.setdefault(
            "country",
            request.env.ref("base.au", raise_if_not_found=False)
            or request.env["res.country"],
        )
        country = qcontext.get("country")
        if country and getattr(country, "id", False):
            qcontext.setdefault(
                "country_states",
                country.state_ids,
            )
        else:
            qcontext.setdefault("country_states", request.env["res.country.state"])
        return qcontext

    def _prepare_signup_values(self, qcontext, *, validate_email=False):
        values = super()._prepare_signup_values(
            qcontext, validate_email=validate_email
        )
        phone = (qcontext.get("phone") or "").strip()
        street = (qcontext.get("street") or "").strip()
        city = (qcontext.get("city") or "").strip()
        zipcode = (qcontext.get("zip") or "").strip()
        street2 = (qcontext.get("street2") or "").strip()

        missing = [
            label
            for label, val in (
                (_("Phone"), phone),
                (_("Street"), street),
                (_("City"), city),
            )
            if not val
        ]
        if missing:
            raise UserError(
                _("Please fill in: %s") % ", ".join(missing)
            )

        values["phone"] = phone
        values["street"] = street
        values["city"] = city
        values["zip"] = zipcode or False
        if street2:
            values["street2"] = street2

        country_id = qcontext.get("country_id")
        if country_id:
            values["country_id"] = int(country_id)
        else:
            au = request.env.ref("base.au", raise_if_not_found=False)
            if au:
                values["country_id"] = au.id

        state_id = qcontext.get("state_id")
        if state_id:
            values["state_id"] = int(state_id)

        return values
