# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.datetime import datetime, relativedelta


class PayslipLinesContributionRegister(models.TransientModel):
    _name = 'payslip.lines.contribution.register'
    _description = 'PaySlip Lines by Contribution Registers'

    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().get_start_month())
    date_to = fields.Date(string='Date To', required=True,
        default=datetime.now() + relativedelta(months=+1, day=1, days=-1))

    @api.multi
    def print_report(self):
        active_ids = self.env.context.get('active_ids', [])
        datas = {
             'ids': active_ids,
             'model': 'hr.contribution.register',
             'form': self.read()[0]
        }
        return self.env.ref('hr_payroll.action_contribution_register').report_action([], data=datas)
