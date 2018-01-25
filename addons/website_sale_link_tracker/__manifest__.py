# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'eCommerce Link Tracker',
    'description': """
View Link Tracker Statistics on eCommerce dashboard
=====================================================

        """,
    'depends': ['website_links', 'website_sale'],
    'category': 'Website',
    'data': [
        'views/sale_order_views.xml',
        'views/assets.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
