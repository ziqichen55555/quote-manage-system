# -*- coding: utf-8 -*-
"""1.0.33 pre: unlock module records so the new snippets + page archs
can be (re)written, and arm the runtime sync flag so the post-migration
also forces COW views to pick up the new structure."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = FALSE
         WHERE module = 'quote_manage_ui'
           AND model IN ('ir.ui.view', 'website.page', 'website.menu')
        """
    )
    cr.execute(
        """
        INSERT INTO ir_config_parameter (key, value, create_date, write_date)
        VALUES ('quote_manage_ui.sync_inline_page_arch_from_xml', 'true', NOW(), NOW())
        ON CONFLICT (key) DO UPDATE
            SET value = 'true', write_date = NOW()
        """
    )
