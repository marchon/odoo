# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ProductUoM(models.Model):
    _inherit = 'product.uom'

    l10n_in_uqc = fields.Char("UQC", help="Unit Quantity Code(UQC) for GSTR Report")
