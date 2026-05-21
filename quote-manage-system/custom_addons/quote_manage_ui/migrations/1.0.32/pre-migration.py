# -*- coding: utf-8 -*-
"""1.0.32: sync COW header/views + menu cleanup (website_id=1 had stale arch)."""


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
