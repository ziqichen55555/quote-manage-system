# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Odoo 17+ passes env (not cr, registry)."""
    method_model = env['account.payment.method'].sudo()
    line_model = env['account.payment.method.line'].sudo()
    journal_model = env['account.journal'].sudo()

    method = method_model.search([
        ('code', '=', 'ebay'),
        ('payment_type', '=', 'inbound'),
    ], limit=1)
    if not method:
        method = method_model.create({
            'name': 'eBay',
            'code': 'ebay',
            'payment_type': 'inbound',
        })

    journals = journal_model.search([('type', 'in', ('bank', 'cash'))])
    if not journals:
        return

    existing_lines = line_model.search([
        ('payment_method_id', '=', method.id),
        ('journal_id', 'in', journals.ids),
    ])
    existing_journal_ids = set(existing_lines.mapped('journal_id').ids)
    missing_journals = journals.filtered(lambda j: j.id not in existing_journal_ids)
    if not missing_journals:
        return

    line_model.create([{
        'name': method.name,
        'payment_method_id': method.id,
        'journal_id': journal.id,
    } for journal in missing_journals])
