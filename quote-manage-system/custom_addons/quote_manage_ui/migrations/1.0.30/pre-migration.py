# -*- coding: utf-8 -*-
"""1.0.30: switch to editor-first policy.

Before this migration the module's ir.ui.view records had
ir.model.data.noupdate = False, so every `-u` overwrote arch_db with whatever
``views/website_templates.xml`` shipped — destroying Website Builder edits on
the homepage, header, /partners, /contactus, …

This pre-migration flips ``noupdate`` to True for all module-owned views BEFORE
the XML loader runs, so the very next `-u` already skips the arch_db rewrite
(the loader does the check in convert.py around line 363:
``if self.noupdate and self.mode != 'init': skip``).

Categories / tags / attributes are also flipped: the backend (or Builder) is
now the source of truth, not the XML.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data
           SET noupdate = TRUE
         WHERE module = 'quote_manage_ui'
           AND model IN (
               'ir.ui.view',
               'website.page',
               'website.menu',
               'product.public.category',
               'product.tag',
               'product.attribute',
               'product.attribute.value'
           )
    """)
