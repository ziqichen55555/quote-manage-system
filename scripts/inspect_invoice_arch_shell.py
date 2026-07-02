from lxml import etree
v = env.ref('account.report_invoice_document')
arch_el = v._get_combined_arch()
arch = etree.tostring(arch_el, encoding='unicode')
print('len:', len(arch))
for key in ['right-elements','payment_term','payment_communication','quote_manage_ui_payment_details','Amount Due','Payment Communication']:
    print(key, '=>', key in arch)
for key in ['right-elements','payment_term','Payment Communication','Amount Due']:
    i = arch.find(key)
    if i!=-1:
        print('\n===', key, 'at', i, '===')
        print(arch[max(0,i-350):i+900])
