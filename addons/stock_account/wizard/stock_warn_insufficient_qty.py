# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models, _


class StockWarnInsufficientQty(models.TransientModel):
    _inherit = 'stock.warn.insufficient.qty.scrap'

    @api.model
    def _default_inventory_message(self):
        scrap_id = self.env['stock.scrap'].browse(self.env.context.get('active_id'))
        invetory_valuation = scrap_id.filtered(lambda l: l.product_id.type == 'product' and l.product_id.categ_id.property_valuation == 'real_time' and l.product_id.lst_price == 0.0)
        prod_lst = scrap_id.mapped('product_id.name')
        msg = _("The cost of <strong>%s</strong> is currently equal to 0,meaning that your product will be valued at 0.Are you sure you want to confirm?" % ','.join(prod_lst))
        if invetory_valuation:
            return msg

    inventory_message = fields.Html(default=_default_inventory_message)
