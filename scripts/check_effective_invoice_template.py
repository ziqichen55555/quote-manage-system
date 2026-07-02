from lxml import etree
v = env.ref('account.report_invoice_document')
arch = etree.tostring(v._get_combined_arch(), encoding='unicode')
checks = [
    'Due Date:',
    'Co-Creative IT Pty Ltd are a local West Australian owned and run company',
    'report_invoice_document_layout_stack_fix_v144',
    'ms-auto',
    'float:none !important',
]
print('module version:', env['ir.module.module'].search([('name','=','quote_manage_ui')], limit=1).installed_version)
for c in checks:
    print(c, '=>', c in arch)
print('len:', len(arch))
