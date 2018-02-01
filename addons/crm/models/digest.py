# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_crm_lead_created = fields.Boolean(string='New Leads/Opportunities')
    kpi_crm_lead_created_value = fields.Integer(compute='_compute_lead_opportunity_value')
    kpi_crm_opportunities_won = fields.Boolean(string='Opportunities Won')
    kpi_crm_opportunities_won_value = fields.Integer(compute='_compute_lead_opportunity_value')

    @api.depends('start_date', 'end_date')
    def _compute_lead_opportunity_value(self):
        CrmLead = self.env['crm.lead']
        for record in self:
            date_domain = [("create_date", ">=", record.start_date), ("create_date", "<=", record.end_date)]
            if self._context.get('timeframe') == 'yesterday':
                date_domain = [("create_date", ">=", record.start_date), ("create_date", "<", record.end_date)]
            lead_created = CrmLead.search_count(date_domain)
            date_domain += [('type', '=', 'opportunity'), ('probability', '=', '100')]
            opp_won = CrmLead.search_count(date_domain)
            record.kpi_crm_lead_created_value = lead_created
            record.kpi_crm_opportunities_won_value = opp_won
