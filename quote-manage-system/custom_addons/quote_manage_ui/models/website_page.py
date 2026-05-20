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


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

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
        """Ensure module menus (Shop, Trade-in, Partners, etc.) are attached to every website's main menu."""
        Menu = self.env['website.menu'].sudo().with_context(active_test=False)
        module_menu_xmlids = [
            'menu_shop',
            'menu_trade_in',
            'menu_services',
            'menu_about_us',
            'menu_our_why',
            'menu_partners',
        ]
        
        for site in Website.search([]):
            main_menu = site.menu_id
            if not main_menu:
                continue
            
            for xmlid in module_menu_xmlids:
                try:
                    menu_record = self.env.ref(f'quote_manage_ui.{xmlid}')
                    # If the menu record exists and is not attached to this website's main menu,
                    # we might need to create a website-specific copy or just ensure the generic one is visible.
                    # Odoo's website.menu is tricky with multi-website.
                    # For now, let's just ensure the XML record's parent is set correctly if it's the only one.
                    if menu_record.parent_id.id != main_menu.id:
                        menu_record.write({'parent_id': main_menu.id})
                except ValueError:
                    continue

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
            'trade_in_page',
            'services_page',
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
