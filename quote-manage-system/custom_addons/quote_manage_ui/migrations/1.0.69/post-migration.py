# -*- coding: utf-8 -*-
"""1.0.69 — Replace the dark placeholder on /aboutus with the Louis & Drew photo.

The original About Us page shipped a CSS-gradient placeholder
(``<div class="rw-about-portrait rw-hero-image rw-hero-image-placeholder">…</div>``)
because the real portrait wasn't available at build time. That element has
no ``<img>`` inside, so Odoo's Website Builder doesn't surface a
"replace media" handle on it.

This migration performs **targeted, idempotent surgery** on the existing
About Us page arch in the database:

* finds every ``ir.ui.view`` whose ``key = 'quote_manage_ui.about_us_page'``
  (generic row + per-website COW copies),
* locates the placeholder div by CSS class (not by exact whitespace), and
* replaces just that node with a real ``<img>`` wrapped in
  ``.rw-about-portrait.rw-about-portrait--photo`` so the rounded card / shadow
  styling stays consistent with the rest of the site.

Views where the placeholder is no longer present (because the user already
edited that block in Website Builder) are left untouched — we never overwrite
neighbouring edits on the About page.
"""
from lxml import etree

from odoo import api, SUPERUSER_ID


PORTRAIT_IMG_SRC = "/quote_manage_ui/static/src/img/team/louis-and-drew.png"
PORTRAIT_IMG_ALT = "Louis and Drew \u2014 Re-Ware Project"


def _build_new_portrait():
    """Return the replacement ``<div>...<img/></div>`` element."""
    wrapper = etree.Element("div")
    wrapper.set("class", "rw-about-portrait rw-about-portrait--photo")
    img = etree.SubElement(wrapper, "img")
    img.set("src", PORTRAIT_IMG_SRC)
    img.set("alt", PORTRAIT_IMG_ALT)
    img.set("class", "img-fluid")
    return wrapper


def _patch_arch(arch_db):
    """Return updated ``arch_db`` or ``None`` if no placeholder was found.

    Parses the fragment under a synthetic ``<root>`` because ``arch_db`` can
    contain multiple top-level nodes (it's a QWeb fragment, not a document).
    Matches by class to be resilient to attribute order / whitespace changes
    that Odoo applies when persisting QWeb.
    """
    if not arch_db:
        return None
    try:
        wrapped = etree.fromstring(
            "<root>%s</root>" % arch_db
        )
    except etree.XMLSyntaxError:
        return None

    targets = wrapped.xpath(
        ".//div[contains(concat(' ', normalize-space(@class), ' '),"
        " ' rw-hero-image-placeholder ')]"
    )
    if not targets:
        return None

    for node in targets:
        parent = node.getparent()
        if parent is None:
            continue
        parent.replace(node, _build_new_portrait())

    return "".join(
        etree.tostring(child, encoding="unicode") for child in wrapped
    )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    View = env["ir.ui.view"].sudo().with_context(active_test=False, no_cow=True)
    views = View.search([
        ("key", "=", "quote_manage_ui.about_us_page"),
        ("type", "=", "qweb"),
    ])

    for view in views:
        new_arch = _patch_arch(view.arch_db)
        if new_arch and new_arch != view.arch_db:
            view.write({"arch_db": new_arch})

    if hasattr(View, "_quote_manage_ui_sync_module_templates_from_xml"):
        View._quote_manage_ui_sync_module_templates_from_xml()

    env["ir.attachment"].sudo().search([
        ("url", "like", "/web/assets/%"),
        ("name", "like", "web.assets_frontend%"),
    ]).unlink()
