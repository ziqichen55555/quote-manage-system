{
    'name': '报价管理系统 后台 UI 改善',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Improve the Backend UI of the quote management system',
    'depends': ['web', 'sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'quote_manage_ui/static/src/scss/backend_style.scss',
        ],
        'web.assets_frontend': [
            'quote_manage_ui/static/src/scss/style.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
