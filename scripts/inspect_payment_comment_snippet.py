from lxml import etree
v = env.ref('account.report_invoice_document')
arch = etree.tostring(v._get_combined_arch(), encoding='unicode')
for key in ['name="payment_communication"','name="comment"','Due Date:']:
    i = arch.find(key)
    print('\nkey', key, 'idx', i)
    if i!=-1:
        print(arch[max(0,i-400):i+1200])
