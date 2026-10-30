# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["website.page"]._quote_manage_ui_apply_seo_metadata()
    for website in env["website"].search([]):
        block = "Disallow: /web/\n"
        robots = website.robots_txt or ""
        if block.strip() not in robots and "Disallow: /web/" not in robots:
            website.robots_txt = (robots.rstrip() + "\n\n" + block).strip() + "\n"
    env.registry.clear_cache()
