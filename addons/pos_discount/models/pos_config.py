# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_discount = fields.Boolean(string='Order Discounts', help='Allow the cashier to give discounts on the whole order.')
    discount_pc = fields.Float(string='Discount Percentage', related='company_id.discount_pc', help='The default discount percentage')
    discount_product_id = fields.Many2one('product.product', string='Discount Product', related='company_id.discount_product_id', domain="[('available_in_pos', '=', True)]", help='The product used to model the discount.')
