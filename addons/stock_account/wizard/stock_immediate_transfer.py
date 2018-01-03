# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    inventory_message = fields.Html(compute='_compute_inventory_message')

    def _compute_inventory_message(self):
        invetory_valuation = self.pick_ids.move_lines.filtered(lambda l: l.product_id.type == 'product' and l.product_id.categ_id.property_valuation == 'real_time' and l.product_id.lst_price == 0.0)
        prod_lst = invetory_valuation.mapped('product_id.name')
        msg = _("The cost of <strong>%s</strong> is currently equal to 0,meaning that your product will be valued at 0.Are you sure you want to confirm?" % ','.join(prod_lst))
        if invetory_valuation:
            self.inventory_message = msg
