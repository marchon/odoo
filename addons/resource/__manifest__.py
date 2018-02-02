# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resource',
    'version': '1.1',
    'category': 'Hidden',
    'website': '',
    'description': """
Module for resource management.
===============================

A resource represent something that can be scheduled (a developer on a task or a
work center on manufacturing orders). This module manages a resource calendar
associated to every resource. It also manages the leaves of every resource.
    """,
    'depends': ['base'],
    'data': [
        'data/resource_data.xml',
        'security/ir.model.access.csv',
        'security/resource_security.xml',
        'views/resource_views.xml',
    ],
    'demo': [
    ],
}
