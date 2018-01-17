# -*- coding: utf-8 -*-

{
    'name': 'Warehouse Management: Push Rules for Sale',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """
This module fixes push rules management for Sale Order Lines
============================================================

Note that this module is not officially supported and is only
provided as a way to apply push rules on sale order lines
according to the configured routes.

This case was not functionnally envisionned when the Stock was
developped, and changing this behaviour so late in the lifecycle
of the 10.0 release would be too dangerous for existing customers
with configuration that work that way.

This module is provided without warranty and should not be considered
as official Odoo code.
    """,
    'website': 'https://www.odoo.com/help',
    'depends': ['stock', 'sale'],
    'author': 'Odoo Support'
    'installable': True,
    'auto_install': False,
}
