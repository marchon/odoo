# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_recruitment_new_colleagues = fields.Boolean(string='New Employees')
    kpi_hr_recruitment_new_colleagues_value = fields.Integer(compute='_compute_kpi_hr_recruitment_new_colleagues_value')

    @api.depends('start_date', 'end_date')
    def _compute_kpi_hr_recruitment_new_colleagues_value(self):
        for record in self:
            date_domain = [("create_date", ">=", record.start_date), ("create_date", "<=", record.end_date)]
            if self._context.get('timeframe') == 'yesterday':
                date_domain = [("create_date", ">=", record.start_date), ("create_date", "<", record.end_date)]
            new_colleagues = self.env['hr.employee'].search_count(date_domain)
            record.kpi_hr_recruitment_new_colleagues_value = new_colleagues
