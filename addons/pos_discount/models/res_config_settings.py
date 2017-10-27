# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount_pc = fields.Float(string='Discount Percentage', related='company_id.discount_pc', help='The default discount percentage')
    discount_product_id = fields.Many2one('product.product', string='Discount Product', domain="[('available_in_pos', '=', True)]", help='The product used to model the discount.', related='company_id.discount_product_id')

    @api.onchange('module_pos_discount')
    def _onchange_module_pos_discount(self):
        if self.module_pos_discount:
            self.discount_product_id = self.discount_product_id or self.company_id._get_default_discount_product()
            self.discount_pc = self.discount_pc or 10.0
        else:
            self.discount_product_id = False
            self.discount_pc = 0.0
