company = env.company
accounts = company._xero_request('GET', 'Accounts', params={'where': 'Type=="BANK"'})
print('Xero BANK accounts:')
for acc in accounts.get('Accounts', []):
    print(' ', acc.get('Code'), '|', acc.get('Name'), '|', acc.get('Status'))
print('\nCurrent Odoo setting xero_bank_account_code:', company.xero_bank_account_code)
print('Current xero_revenue_account_code:', company.xero_revenue_account_code)
