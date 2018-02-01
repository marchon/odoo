# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_website_sale_total = fields.Boolean(string='eCommerce Sales')
    kpi_website_sale_total_value = fields.Monetary(compute='_compute_kpi_website_sale_total_value')

    @api.depends('start_date', 'end_date')
    def _compute_kpi_website_sale_total_value(self):
        for record in self:
            date_domain = [("date_order", ">=", record.start_date), ("date_order", "<=", record.end_date)]
            if self._context.get('timeframe') == 'yesterday':
                date_domain = [("date_order", ">=", record.start_date), ("date_order", "<", record.end_date)]
            date_domain += [('state', 'not in', ['draft', 'cancel', 'sent']), ('team_id.team_type', '=', 'website')]
            confirmed_website_sales = self.env['sale.order'].search(date_domain)
            record.kpi_website_sale_total_value = sum(confirmed_website_sales.mapped('amount_total'))
