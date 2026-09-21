{
    'name': 'Dental Lab Management',
    'version': '18.0.1.0.0',
    'category': 'Services/Dental Lab',
    'summary': 'Manage dental prosthesis work orders between dentists and the lab',
    'description': """
        Dental Lab Management
        ======================
        Allows dentists (portal users) to submit dental prosthesis work orders,
        and lab technicians/managers to process, track and complete them.
    """,
    'author': 'W.Demdoum',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/dental_lab_security.xml',
        'security/ir.model.access.csv',
        'data/dental_lab_sequence.xml',
        'views/dental_lab_order_views.xml',
        'views/dental_lab_menus.xml',
        'views/portal_templates.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            'dental_lab/static/src/js/dental_lab_portal.js',
            'dental_lab/static/src/scss/portal.scss',
        ],
    },
}
