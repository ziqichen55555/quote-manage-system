# -*- coding: utf-8 -*-
import os
from xml.etree import ElementTree as ET

from odoo import api, models
from odoo.tools.misc import file_path


def _quote_manage_ui_website_templates_xml_path():
    """Absolute path to ``views/website_templates.xml`` (Odoo 17+ ``file_path`` API)."""
    try:
        return file_path('quote_manage_ui/views/website_templates.xml')
    except (FileNotFoundError, ValueError):
        return False


def _quote_manage_ui_template_xml_paths():
    """All XML files in this module that contain ``<template>`` declarations.

    Used by the sync helpers so that newly added snippet libraries (e.g.
    ``views/snippets.xml``) are picked up alongside ``website_templates.xml``
    without needing to update every helper individually.
    """
    paths = []
    for rel in ('quote_manage_ui/views/website_templates.xml',
                'quote_manage_ui/views/snippets.xml'):
        try:
            paths.append(file_path(rel))
        except (FileNotFoundError, ValueError):
            continue
    return paths


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _quote_manage_ui_read_template_arch_from_xml(self, template_id, root=None):
        """Return ``arch_db`` string for a ``<template id="…">`` in any module XML.

        ``root`` may be a single ElementTree root (legacy callers) or an
        iterable of roots (multi-file lookup). When omitted, every file
        returned by :func:`_quote_manage_ui_template_xml_paths` is searched
        and the first match wins.
        """
        if root is None:
            roots = []
            for path in _quote_manage_ui_template_xml_paths():
                if not os.path.isfile(path):
                    continue
                try:
                    roots.append(ET.parse(path).getroot())
                except ET.ParseError:
                    continue
        elif isinstance(root, (list, tuple)):
            roots = list(root)
        else:
            roots = [root]

        for r in roots:
            for tmpl in r.findall('.//template'):
                if tmpl.get('id') != template_id:
                    continue
                inner = ''.join(
                    ET.tostring(child, encoding='unicode') for child in list(tmpl)
                ).strip()
                inherit_id = tmpl.get('inherit_id')
                if inherit_id:
                    attrs = [
                        f'inherit_id="{inherit_id}"',
                        f'name="{tmpl.get("name", "")}"',
                    ]
                    if tmpl.get('priority'):
                        attrs.append(f'priority="{tmpl.get("priority")}"')
                    return f'<data {" ".join(attrs)}>{inner}</data>'
                return inner
        return None

    @api.model
    def _quote_manage_ui_sync_module_templates_from_xml(self):
        """Push every module-owned ``<template>`` onto its COW copies.

        Website Builder creates per-website ``ir.ui.view`` rows (same ``key``,
        different ``website_id``) whose ``arch_db`` can stay on an old header /
        homepage extension after ``-u``. This walks both ``website_templates.xml``
        and ``snippets.xml`` and rewrites every matching COW row so the latest
        snippet structure is the one users see.
        """
        roots = []
        for path in _quote_manage_ui_template_xml_paths():
            if not os.path.isfile(path):
                continue
            try:
                roots.append(ET.parse(path).getroot())
            except ET.ParseError:
                continue
        template_ids = []
        seen = set()
        for r in roots:
            for el in r.findall('.//template'):
                tid = el.get('id')
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                template_ids.append(tid)

        View = self.sudo().with_context(active_test=False)
        for tid in template_ids:
            arch_db = self._quote_manage_ui_read_template_arch_from_xml(tid, root=roots)
            if not arch_db:
                continue
            view_key = f'quote_manage_ui.{tid}'
            for view in View.search([('key', '=', view_key)]):
                view.write({'arch_db': arch_db})

    @api.model
    def _quote_manage_ui_lock_module_archs(self):
        """Editor-first policy: lock arch_db of all quote_manage_ui-owned views.

        Sets ``ir.model.data.noupdate = True`` on every record this module owns
        across the layout-bearing models. Once locked, the next `-u` short-
        circuits in ``odoo/tools/convert.py`` (`if self.noupdate and self.mode
        != 'init': return`) before re-writing fields, so Website Builder edits
        on the homepage / header / /partners / /contactus / category names /
        menu order stay across upgrades.

        Re-run idempotently at the end of every upgrade so newly added views
        (e.g. when bumping to 1.0.31+) are auto-locked after their first load.
        To intentionally redeploy XML, clear ``noupdate`` on the specific
        ir.model.data row before `-u`.
        """
        self.env['ir.model.data'].sudo().search([
            ('module', '=', 'quote_manage_ui'),
            ('model', 'in', (
                'ir.ui.view',
                'website.page',
                'website.menu',
                'product.public.category',
                'product.tag',
                'product.attribute',
                'product.attribute.value',
            )),
            ('noupdate', '=', False),
        ]).write({'noupdate': True})


class WebsitePage(models.Model):
    _inherit = 'website.page'

    @api.model
    def _quote_manage_ui_fix_homepage_view(self):
        """Point / website.page at the active primary website.homepage (COW).

        After editing the homepage in the Website Builder, Odoo can leave
        website.page.view_id on an inactive duplicate while extensions from
        modules attach to the active COW view — so / never picks up template
        changes. Repoint to the active primary view for each website.

        Also clear ``website.homepage_url`` when it was set to a duplicate path
        like ``/home-reware`` so the controller serves the real ``/`` page and
        module QWeb (priority) stays predictable.

        Removes legacy ``quote_manage_ui.reware_homepage_primary`` views: a
        flattened merged primary arch prevented proper ``o_editable`` / drop
        zones, so building blocks (e.g. Carousel) appeared undroppable.

        **Partners URL:** a page created with **Site → New Page** at ``/partners``
        is a different ``website.page`` (other ``key``, usually website-specific). It
        wins in ``_serve_page`` search order over the module page, so XML / ``-u``
        looks like it does nothing. We remove those duplicate URLs and repoint
        menus to the module page.

        **Inline page arch (About, Services, …):** optional. By default we do **not**
        push ``website_templates.xml`` into the database on every module upgrade,
        so **Website Builder** edits stay. Set system parameter
        ``quote_manage_ui.sync_inline_page_arch_from_xml`` to ``true`` before
        ``-u`` when you need to redeploy QWeb from the module file (e.g. after
        changing inline ``website.page`` XML). When enabled, we write arch to
        every ``ir.ui.view`` with the same page ``key`` (generic + COW copies).
        """
        View = self.env['ir.ui.view'].sudo()
        Website = self.env['website'].sudo()
        Page = self.sudo().with_context(active_test=False)
        # NOTE: We used to reset noupdate=False on quote_refurb_% and public_cat_%
        # ir.model.data rows here so that XML reapplied on -u. That silently undid
        # backend edits (category names, tag colors, attribute values) every upgrade.
        # Policy is now editor-first: XML seeds once, the database is the source of
        # truth afterwards. To force-resync from XML, set the system parameter
        # 'quote_manage_ui.sync_inline_page_arch_from_xml' to True before -u and
        # manually clear noupdate on the records you want pushed.
        def _homepage_primary_domain(website):
            dom = [
                ('key', '=', 'website.homepage'),
                ('mode', '=', 'primary'),
                ('active', '=', True),
            ]
            dom.append(
                ('website_id', '=', website.id) if website else ('website_id', '=', False)
            )
            return dom

        for page in Page.search([('url', '=', '/')]):
            # Editor-first: only repoint when the current view_id is missing or
            # disabled. Otherwise leave the Website Builder's COW copy alone --
            # `limit=1` on the domain below could pick the *wrong* primary view
            # (multiple COW copies in the wild) and silently roll the homepage back.
            current = page.view_id
            if current and current.active and current.key == 'website.homepage' and current.mode == 'primary':
                continue
            website = page.website_id
            active = View.search(_homepage_primary_domain(website), limit=1)
            if active and page.view_id.id != active.id:
                page.write({'view_id': active.id})
        # Reroute was hiding changes: / -> homepage_url (e.g. /home-reware) with separate menu perception
        for site in Website.search(
            [('homepage_url', 'in', ('/home-reware', '/-1'))]
        ):
            site.homepage_url = False

        # Legacy: a "baked" merged primary view (key quote_manage_ui.reware_homepage_primary)
        # broke Website Builder — snippets need #wrap (oe_structure) with normal ir.ui.view
        # branding / o_editable. Remove leftovers and rely on website.homepage + extensions.
        legacy = View.search([('key', '=', 'quote_manage_ui.reware_homepage_primary')])
        if legacy:
            for page in Page.search([('view_id', 'in', legacy.ids)]):
                website = page.website_id
                active = View.search(_homepage_primary_domain(website), limit=1)
                if active:
                    page.write({'view_id': active.id})
            legacy.unlink()

        self._quote_manage_ui_ensure_partners_module_page(Page)
        self._quote_manage_ui_ensure_menu_parents(Website)

        # Legacy: old About page used a separate QWeb template; About is now inline like Services.
        for orphan in View.search([('key', '=', 'quote_manage_ui.about_us_page_template')]):
            if not Page.search_count([('view_id', '=', orphan.id)]):
                orphan.unlink()

        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param(
            'quote_manage_ui.sync_inline_page_arch_from_xml', 'false'
        ).lower() in ('1', 'true', 'yes'):
            self._quote_manage_ui_sync_inline_page_archs_from_module_xml()
            self.env['ir.ui.view']._quote_manage_ui_sync_module_templates_from_xml()
            self._quote_manage_ui_cleanup_duplicate_menus()

        # Allow website.page XML to overwrite DB on subsequent upgrades (same idea as refurb data).
        # DEPRECATED: This was erasing user edits on every upgrade. 
        # Use the system parameter 'quote_manage_ui.sync_inline_page_arch_from_xml' instead.
        # self.env['ir.model.data'].sudo().search([
        #     ('module', '=', 'quote_manage_ui'),
        #     ('model', '=', 'website.page'),
        # ]).write({'noupdate': False})

    @api.model
    def _quote_manage_ui_ensure_partners_module_page(self, Page):
        """One canonical /partners page: module key ``quote_manage_ui.partners_page``.

        Editor-created pages at /partners that use a DIFFERENT key (e.g. via
        Site → New Page) shadow the module page in ``_serve_page``. Remove only
        those foreign-key duplicates and repoint menus. Website-specific COW
        copies of the module page share the same key and MUST be preserved
        (``website_id`` differs) — they hold the user's Website Builder edits.
        """
        Menu = self.env['website.menu'].sudo().with_context(active_test=False)
        KEY = 'quote_manage_ui.partners_page'
        Page = Page.sudo()
        # Prefer the generic (website_id=False) row as canonical; COW copies keep
        # the same key but have website_id set and stay untouched.
        mod = Page.search([('key', '=', KEY), ('website_id', '=', False)], limit=1)
        if not mod:
            mod = Page.search([('key', '=', KEY)], limit=1)
        foreign = Page.search([
            ('url', 'in', ('/partners', '/partners/')),
            ('key', '!=', KEY),
        ])
        if foreign:
            if mod:
                Menu.search([('page_id', 'in', foreign.ids)]).write({'page_id': mod.id})
            foreign.unlink()
        if not Page.search([('key', '=', KEY)]):
            _pk, arch = self._quote_manage_ui_read_page_record_xml('partners_page')
            if arch:
                mod = Page.create({
                    'name': 'Our Partners',
                    'url': '/partners',
                    'type': 'qweb',
                    'is_published': True,
                    'website_indexed': True,
                    'key': KEY,
                    'arch': arch,
                })
        if mod:
            Menu.search([
                ('url', 'in', ('/partners', '/partners/')),
                '|', ('page_id', '=', False), ('page_id', '!=', mod.id),
            ]).write({'page_id': mod.id, 'url': '/partners'})

    @api.model
    def _quote_manage_ui_read_page_record_xml(self, record_id, root=None):
        """Return ``(key, arch_db)`` for a ``<record model='website.page' id=…>`` in module XML."""
        if root is None:
            path = _quote_manage_ui_website_templates_xml_path()
            if not path or not os.path.isfile(path):
                return None, None
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                return None, None
        for record in root.findall('.//record'):
            if record.get('id') != record_id:
                continue
            if record.get('model') != 'website.page':
                continue
            page_key = None
            arch_db = None
            for field in record.findall('field'):
                fname = field.get('name')
                if fname == 'key':
                    if field.text and field.text.strip():
                        page_key = field.text.strip()
                elif fname == 'arch':
                    arch_db = ''.join(
                        ET.tostring(child, encoding='unicode') for child in list(field)
                    ).strip()
            return page_key, arch_db
        return None, None

    @api.model
    def _quote_manage_ui_ensure_menu_parents(self, Website):
        """Re-attach module menus to each website's top menu (dedupe included)."""
        self._quote_manage_ui_cleanup_duplicate_menus()

    @api.model
    def _quote_manage_ui_sync_inline_page_archs_from_module_xml(self):
        """Copy ``website.page`` arch from ``website_templates.xml`` onto DB views.

        Writes ``arch_db`` to every ``ir.ui.view`` with the page ``key`` (type
        qweb), including **website COW copies**, not only the generic
        ``page.view_id``. Otherwise the live site keeps rendering an empty
        website-specific view after edits in the Website Builder.
        """
        path = _quote_manage_ui_website_templates_xml_path()
        if not path or not os.path.isfile(path):
            return
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            return
        record_xmlids = (
            'about_us_page',
            'our_why_page',
            'partners_page',
        )
        View = self.env['ir.ui.view'].sudo().with_context(active_test=False, no_cow=True)
        for rid in record_xmlids:
            page_key, arch_db = self._quote_manage_ui_read_page_record_xml(rid, root=root)
            if not page_key or not arch_db:
                continue
            for v in View.search([('key', '=', page_key), ('type', '=', 'qweb')]):
                v.write({'arch_db': arch_db})

    @api.model
    def _quote_manage_ui_cleanup_duplicate_menus(self):
        """One Re-Ware nav: About. / Our Why. / Contact. + DONATE / SHOP buttons.

        Hidden from the navigation (their page records stay so direct URLs
        keep working): ``/shop``, ``/partners``, ``/trade-in``, ``/services``.
        Trade-in and Services pages are also fully removed (legacy URLs).
        The seeded ``/contactus`` menu is reattached under each website's
        main menu and renamed to ``Contact.`` at sequence 3 so it shows up
        in both the desktop nav and the mobile offcanvas.
        """
        Menu = self.env['website.menu'].sudo().with_context(active_test=False)
        Page = self.env['website.page'].sudo().with_context(active_test=False)
        View = self.env['ir.ui.view'].sudo().with_context(active_test=False)
        ModelData = self.env['ir.model.data'].sudo()
        Website = self.env['website'].sudo()
        # Typo from an old Website Builder page (/partners-10).
        Menu.search([
            '|',
            ('url', '=', '/partners-10'),
            ('name', 'ilike', 'Patner'),
        ]).unlink()

        # ---- Drop Trade-in / Services from the navigation entirely --------
        retired_urls = ('/trade-in', '/services')
        retired_keys = (
            'quote_manage_ui.trade_in_page',
            'quote_manage_ui.services_page',
        )
        retired_menu_xmlids = (
            'menu_trade_in', 'menu_services', 'menu_shop', 'menu_partners',
        )

        # Menus first (FK on website.menu.page_id would block page unlink).
        Menu.search([('url', 'in', retired_urls)]).unlink()
        # /shop and /partners menus hidden (page records kept for direct URLs).
        Menu.search([('url', 'in', ('/shop', '/partners', '/partners/'))]).unlink()
        # Pages and their COW copies.
        retired_pages = Page.search([
            '|',
            ('url', 'in', retired_urls),
            ('key', 'in', retired_keys),
        ])
        retired_view_ids = retired_pages.mapped('view_id').ids
        retired_pages.unlink()
        # ir.ui.view rows that backed those pages (generic + per-website COW).
        View.search([
            '|',
            ('id', 'in', retired_view_ids),
            ('key', 'in', retired_keys),
        ]).unlink()
        # ir.model.data references so a future -u doesn't try to recreate them.
        ModelData.search([
            ('module', '=', 'quote_manage_ui'),
            '|',
            ('name', 'in', retired_menu_xmlids),
            ('name', 'in', ('trade_in_page', 'services_page')),
        ]).unlink()

        menu_specs = (
            ('menu_about_us', 'About.', 1),
            ('menu_our_why', 'Our Why.', 2),
        )
        for site in Website.search([]):
            main_menu = site.menu_id
            if not main_menu:
                continue
            for xmlid, label, seq in menu_specs:
                try:
                    mod_menu = self.env.ref(f'quote_manage_ui.{xmlid}')
                except ValueError:
                    continue
                mod_menu.write({
                    'name': label,
                    'parent_id': main_menu.id,
                    'website_id': site.id,
                    'sequence': seq,
                })
                Menu.search([
                    ('url', '=', mod_menu.url),
                    ('parent_id', '=', main_menu.id),
                    ('id', '!=', mod_menu.id),
                ]).unlink()

            # Reattach the seeded /contactus menu under this website's main
            # menu (it lands at parent_id=1 / generic root by default, which
            # makes it invisible in the per-website nav). Rename to
            # "Contact." and put it at sequence 3 so the order is
            # About. / Our Why. / Contact. — matching the design.
            site_contact = Menu.search([
                ('parent_id', '=', main_menu.id),
                ('url', '=', '/contactus'),
            ], limit=1)
            if not site_contact:
                generic_contact = Menu.search([
                    ('url', '=', '/contactus'),
                    '|', ('parent_id', '!=', main_menu.id),
                    ('parent_id', '=', False),
                ], limit=1)
                if generic_contact:
                    generic_contact.write({
                        'parent_id': main_menu.id,
                        'website_id': site.id,
                        'name': 'Contact.',
                        'sequence': 3,
                    })
                    site_contact = generic_contact
            else:
                site_contact.write({'name': 'Contact.', 'sequence': 3})
            if site_contact:
                Menu.search([
                    ('parent_id', '=', main_menu.id),
                    ('url', '=', '/contactus'),
                    ('id', '!=', site_contact.id),
                ]).unlink()

            # Re-sweep retired menus that may have been re-seeded by COW.
            Menu.search([
                ('parent_id', '=', main_menu.id),
                '|', '|',
                ('url', 'in', retired_urls + ('/shop', '/partners', '/partners/')),
                ('name', '=', 'Shop'),
                ('name', '=', 'Partners'),
            ]).unlink()
