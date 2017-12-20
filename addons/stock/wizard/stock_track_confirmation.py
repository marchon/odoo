# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class StockTrackConfirmation(models.TransientModel):
    _name = 'stock.track.confirmation'

    track_products = fields.Html(compute='_compute_track_products')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')

    def _compute_track_products(self):
        tracking = {'lot': "Tracked by lot", 'serial': "Tracked by serial number"}
        inventory_lines = self.inventory_id.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id)
        tracking_details = ''
        if inventory_lines:
            product_names = '<br/>'.join(inventory_lines.mapped('product_id.display_name'))
            tracking_display = '<br/>'.join([tracking[product.tracking] for product in inventory_lines.mapped('product_id')])
            tracking_details += '<table><tr><td style="padding: 20px;text-align: left;">%s</td><td>%s</td></tr></table>' % (product_names, tracking_display)
        self.track_products = tracking_details

    @api.one
    def action_confirm(self):
        return self.inventory_id.action_done()
