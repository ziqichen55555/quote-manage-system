reports = env['ir.actions.report'].search([('model','=','account.move'),('report_type','=','qweb-pdf')])
for r in reports:
    if 'invoice' in (r.report_name or '').lower() or 'invoice' in (r.name or '').lower() or 'tax' in (r.name or '').lower():
        print(r.id, '|', r.name, '|', r.report_name, '|', r.report_file)
