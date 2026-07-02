from lxml import etree
v = env.ref('account.report_invoice_document')
arch = etree.tostring(v._get_combined_arch(), encoding='unicode')
for key in ['0499 909 302','0411 882 377','re-ware@cocreativeit.com','reware-comment-block']:
    print(key, '=>', key in arch)
company = env.company
print('report_footer:', (company.report_footer or '')[:500])
