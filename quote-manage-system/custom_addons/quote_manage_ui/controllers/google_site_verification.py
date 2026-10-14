# -*- coding: utf-8 -*-
"""Serve Google Search Console HTML verification at site root (no UI impact)."""
from odoo import http
from odoo.http import request

# Content must match the file Google gave you (one line). If Verify fails, open your
# downloaded googlec499c9fd6e43910e.html and replace this string to match exactly.
_GSC_HTML_BODY = "google-site-verification: googlec499c9fd6e43910e.html"


class GoogleSiteVerification(http.Controller):
    @http.route(
        "/googlec499c9fd6e43910e.html",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        cors="*",
    )
    def google_search_console_html(self):
        return request.make_response(
            _GSC_HTML_BODY,
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )
