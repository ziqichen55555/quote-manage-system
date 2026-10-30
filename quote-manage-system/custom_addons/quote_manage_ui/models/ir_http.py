# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)
        if not request or not getattr(request, "httprequest", None):
            return
        path = (request.httprequest.path or "").split("?", 1)[0].rstrip("/") or "/"
        noindex_paths = {"/web/login", "/web/signup", "/web/reset_password"}
        if path in noindex_paths or path.startswith("/web/database"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
