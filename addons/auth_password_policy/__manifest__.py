{
    'name': "Password Policy",
    "summary": "Implements basic password policy configuration & check",
    'depends': ['base_setup', 'auth_crypt', 'web'],
    'data': [
        'data/defaults.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
    ]
}
