# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'MRP Byproducts',
    'version': '1.0',
    'category': 'Operations',
    'description': """
This module allows you to produce several products from one production order.
=============================================================================

You can configure by-products in the bill of material.

Without this module:
--------------------
    A + B + C -> D

With this module:
-----------------
    A + B + C -> D + E
    """,
    'website': '',
    'depends': ['base', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
