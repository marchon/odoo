# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models


class StockInventoryValuation(models.TransientModel):
    _name = 'stock.inventory.valuation'
    _description = 'Inventory Valuation'

    inventory_message = fields.Char()
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    product_change_quantity_id = fields.Many2one('stock.change.product.qty', 'Change Quantity')

    @api.multi
    def action_confirm(self):
        if self.inventory_id:
            return self.inventory_id.action_done()
        if self.picking_id:
            return self.picking_id.button_validate()
        if self.product_change_quantity_id:
            return self.product_change_quantity_id.change_product_qty()
