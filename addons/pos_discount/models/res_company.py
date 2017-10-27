# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_discount_product(self):
        return self.env.ref('point_of_sale.product_product_consumable')

    discount_product_id = fields.Many2one('product.product', string='Discount Product', domain="[('available_in_pos', '=', True)]", default=_get_default_discount_product, help='The product used to model the discount.')
    discount_pc = fields.Float(string='Discount Percentage', help='The default discount percentage', default=10.0)
