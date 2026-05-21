# -*- coding: utf-8 -*-
"""1.0.31: Re-Ware visual rebuild — push module XML into DB once.

Phase 1 (this file, pre-migration): unlock ``ir.model.data.noupdate`` on all
module-owned views / pages / menus so the standard XML loader (running right
after this) will rewrite ``arch_db`` from ``views/website_templates.xml``.

Phase 2 (XML load): website_templates.xml is parsed and writes arch_db onto
existing ir.ui.view rows and website.page rows that share the module xml_id.

Phase 3 (post-migration.py): force a sync onto website-specific COW copies of
the inline pages (about_us_page etc.), then let zz_lock_module_archs.xml lock
everything down again on the same -u.
"""


def migrate(cr, version):
    # Allow XML to overwrite arch_db / fields on existing records.
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = FALSE
         WHERE module = 'quote_manage_ui'
           AND model IN (
               'ir.ui.view',
               'website.page',
               'website.menu'
           )
        """
    )

    # Tell the post-load hook to push module XML arch onto website COW copies.
    cr.execute(
        """
        INSERT INTO ir_config_parameter (key, value, create_date, write_date)
        VALUES ('quote_manage_ui.sync_inline_page_arch_from_xml', 'true', NOW(), NOW())
        ON CONFLICT (key) DO UPDATE
            SET value = 'true', write_date = NOW()
        """
    )
