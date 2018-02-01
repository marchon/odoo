# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_account_bank_cash = fields.Boolean(string='Bank & Cash')
    kpi_account_bank_cash_value = fields.Integer(compute='_compute_kpi_account_total_revenue_value')
    kpi_account_total_revenue = fields.Boolean(string='Revenue')
    kpi_account_total_revenue_value = fields.Integer(compute='_compute_kpi_account_total_revenue_value')

    @api.depends('start_date', 'end_date')
    def _compute_kpi_account_total_revenue_value(self):

        def _account_move_amount(journal_type):
            return sum(account_moves.filtered(lambda r: r.journal_id.type in journal_type).mapped('amount'))

        for record in self:
            date_domain = [("create_date", ">=", record.start_date), ("create_date", "<=", record.end_date)]
            if self._context.get('timeframe') == 'yesterday':
                date_domain = [("create_date", ">=", record.start_date), ("create_date", "<", record.end_date)]
            date_domain += [('journal_id.type', 'in', ['sale', 'cash', 'bank'])]
            account_moves = self.env['account.move'].search(date_domain)
            record.kpi_account_total_revenue_value = _account_move_amount(['sale'])
            record.kpi_account_bank_cash_value = _account_move_amount(['bank', 'cash'])
