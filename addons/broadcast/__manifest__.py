# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Broadcast Video conferencing',
    'version': '1.0',
    'category': 'Discuss',
    'description': "",
    'depends': ['mail'],
    'data': [
        'views/broadcast_templates.xml',
    ],
    'qweb': [
        'static/src/xml/broadcast.xml',
    ],
    'installable': True,
    'application': True,
}
