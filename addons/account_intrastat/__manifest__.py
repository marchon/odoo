# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Intrastat & EC Sales List',
    'category': 'Accounting',
    'description': """
A module that adds intrastat reports.
=====================================

This module gives the details of the goods traded between the countries of
European Union.""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/country_data.xml',
        'views/intrastat_code_views.xml',
        'views/product_views.xml',
        'views/country_views.xml',
    ],
}
