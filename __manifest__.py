{
    'name': 'Dashboard Remoto',
    'version': '16.0.9.0.0',
    'category': 'Inventory',
    'summary': 'Dashboards múltiples conectados a Odoo 18 remoto',
    'description': """
        Módulo que se conecta por API (XML-RPC) a un Odoo 18 remoto y muestra
        dashboards configurables con columnas:
        - En Preparación / Despachar (opcionales)
        - Mostrador – En Preparación / Listo para Entregar (con split automático)
        - Filtros remotos, múltiples dashboards, sync por config.
    """,
    'author': 'Printemps',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/remote_config_views.xml',
        'views/remote_log_views.xml',
        'views/menu.xml',
        'data/cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'remote_dashboard/static/src/css/dashboard.css',
            'remote_dashboard/static/src/js/dashboard.js',
            'remote_dashboard/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
