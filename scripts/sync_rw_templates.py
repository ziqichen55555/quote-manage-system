"""Push quote_manage_ui snippet/template XML into locked ir.ui.view rows.

Website Builder sets noupdate on module views, so ``-u quote_manage_ui`` alone
may not refresh snippets like s_rw_hero. Run after every module upgrade.
"""
env['ir.ui.view']._quote_manage_ui_sync_module_templates_from_xml()
env['website.page']._quote_manage_ui_sync_inline_page_archs_from_module_xml()
env['ir.attachment'].sudo().search([
    ('url', 'like', '/web/assets/%'),
    ('name', 'like', 'web.assets_frontend%'),
]).unlink()
env.cr.commit()
print('Synced quote_manage_ui templates + page archs from XML.')
