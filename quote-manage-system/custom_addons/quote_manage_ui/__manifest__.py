{
    'name': '报价管理系统 后台 UI 改善',
    'version': '1.0.149',
    'category': 'Hidden',
    'summary': 'Improve the Backend UI of the quote management system',
    'depends': [
        'account',
        'delivery',
        'l10n_au',
        'web',
        'sale',
        'stock',
        'website',
        'website_sale',
        'website_sale_stock',
        'website_blog',
        'website_crm',
        'product_images',
        'mass_mailing',
    ],
    'data': [
        'data/quote_refurb_product_category.xml',
        'data/quote_refurb_product_tags.xml',
        'data/quote_refurb_product_attributes.xml',
        'data/delivery_shipping_rules.xml',
        'data/stock_serial_tracking_enable.xml',
        # Product rows are imported via scripts/import_products_to_odoo.sh;
        # loading them on every -u hits duplicate barcode errors.
        'data/quote_manage_ui_arch_sync_policy.xml',
        # Snippets must be declared BEFORE website_templates.xml so the
        # <t t-call="quote_manage_ui.s_rw_*"/> references inside page archs
        # resolve cleanly during the same data-load.
        'views/snippets.xml',
        'views/website_legal_pages.xml',
        'views/report_invoice_templates.xml',
        'views/website_templates.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/product_import_wizard_views.xml',
        'views/crm_lead_views.xml',
        'security/ir.model.access.csv',
        'data/website_homepage_fix.xml',
        # MUST be last: locks ir.model.data.noupdate=True on layout records so
        # subsequent `-u` skips arch_db rewrites and preserves Builder edits.
        'data/zz_lock_module_archs.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'quote_manage_ui/static/src/scss/report_invoice.scss',
        ],
        'web.assets_backend': [
            'quote_manage_ui/static/src/scss/backend_style.scss',
        ],
        'web.assets_frontend': [
            'quote_manage_ui/static/src/scss/style.scss',
            'quote_manage_ui/static/src/js/newsletter.js',
            'quote_manage_ui/static/src/js/hero_carousel.js',
            'quote_manage_ui/static/src/js/website_stock_qty.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
