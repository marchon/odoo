# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def button_validate(self):
        invetory_valuation = self.move_lines.filtered(lambda l: l.product_id.type == 'product' and l.product_id.categ_id.property_valuation == 'real_time' and l.product_id.lst_price == 0.0)
        no_quantities_done = all(line.qty_done == 0.0 for line in self.move_line_ids)
        if no_quantities_done:
            return super(Picking, self).button_validate()
        elif invetory_valuation and not self._context.get('need_confirm'):
            prod_lst = invetory_valuation.mapped('product_id.name')
            return {
                'name': _('Inventory Valuation'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.inventory.valuation',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_inventory_message': ','.join(prod_lst),
                    'default_picking_id': self.id,
                }
            }
        return super(Picking, self).button_validate()


class Inventory(models.Model):
    _inherit = "stock.inventory"

    @api.multi
    def action_done(self):
        for stock_inventory in self:
            invetory_valuation = stock_inventory.line_ids.filtered(lambda l: l.product_id.type == 'product' and l.product_id.categ_id.property_valuation == 'real_time' and  l.product_id.lst_price == 0.0)
            if invetory_valuation and not self._context.get('need_confirm'):
                prod_lst = invetory_valuation.mapped('product_id.name')
                return {
                    'name': _('Inventory Valuation'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.inventory.valuation',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {
                        'default_inventory_message': ','.join(prod_lst),
                        'default_inventory_id': self.id
                    },
                }
            return super(Inventory, self).action_done()


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    @api.multi
    def action_validate(self):
        return super(StockScrap, self).action_validate()


class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    @api.multi
    def change_product_qty(self):
        invetory_valuation = self.product_id.type == 'product' and self.product_id.categ_id.property_valuation == 'real_time' and self.product_id.lst_price == 0.0
        if invetory_valuation and not self._context.get('need_confirm'):
            return {
                'name': _('Inventory Valuation'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.inventory.valuation',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_inventory_message': self.product_id.name,
                    'default_product_change_quantity_id': self.id,
                }
            }
        return super(ProductChangeQuantity, self).change_product_qty()
