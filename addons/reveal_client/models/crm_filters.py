# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import math

from odoo import api, fields, models
from odoo.addons.iap import jsonrpc, InsufficientCreditError
from odoo.addons.crm.models import crm_stage

_logger = logging.getLogger(__name__)

# TODO: replace it with our server's url
DEFAULT_ENDPOINT = 'http://localhost:8069/reveal'

class CRMLeadRule(models.Model):

    _name = 'reveal.lead.rule'
    _description = 'Reveal Lead Rules'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)

    # Website Traffic Filter
    country_ids = fields.Many2many('res.country', string='Countries')
    regex_url = fields.Char(string='URL Regex')

    # Company Criteria Filter
    industry_tag_ids = fields.Many2many('reveal.industry.tag', string="Industry Tags")
    company_size_min = fields.Integer(string='Company Size Min', help="fill 0 if you don't want this filter to check")
    company_size_max = fields.Integer(string='Company Size Max', help="fill 0 if you don't want this filter to check")

    # Contact Generation Filter
    preferred_role_id = fields.Many2one('reveal.people.role', string="Preferred Role")
    other_role_ids = fields.Many2many('reveal.people.role', string="Other Roles")
    seniority_id = fields.Many2one('reveal.people.seniority', string="Seniority")
    extra_contacts = fields.Integer(string="Extra Contacts")

    calculate_credits = fields.Integer(compute='_credit_count', string="Credit Used", readonly=True)

    # Lead / Opportunity Data
    lead_for = fields.Selection([('companies', 'Companies'), ('people', 'People')], string='Generate Leads For', required=True, default="people")
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default="opportunity")
    suffix = fields.Char(string='Suffix')
    team_id = fields.Many2one('crm.team', string='Sales Channel')
    stage_id = fields.Many2one('crm.stage', string='Stage')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    lead_ids = fields.One2many('crm.lead', 'reveal_rule_id', string="Generated Lead / Opportunity")
    leads_count = fields.Integer(compute='_compute_leads_count', string="Number of Generated Leads")

    @api.multi
    def _compute_leads_count(self):
        leads = self.env['crm.lead'].read_group([
            ('reveal_rule_id', 'in', self.ids)
        ], fields=['reveal_rule_id'], groupby=['reveal_rule_id'])
        mapping = dict([(lead['reveal_rule_id'][0], lead['reveal_rule_id_count']) for lead in leads])
        for rule in self:
            rule.leads_count = mapping.get(rule.id, 0)

    @api.multi
    def action_get_lead_tree_view(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids)]
        return action

    @api.multi
    @api.depends('extra_contacts')
    @api.onchange('extra_contacts', 'lead_for')
    def _credit_count(self):
        credit = 1 
        if self.lead_for == 'people':
            credit += 1
            if self.extra_contacts:
                credit += self.extra_contacts
        self.calculate_credits = credit

    # TODO: remove this method just for test
    @api.multi
    def test_rule(self):
        return {
            'name': 'action_test_rule',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'reveal.test.rule',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.model
    def process_reveal_request(self, path, ip):
        lead_exist = self.env['crm.lead'].with_context(active_test=False).search_count([('reveal_ip', '=', ip)])
        if not lead_exist:
            rules = self._get_matching_rules(path)
            if rules:
                rule_data = rules._get_data_for_server()
                self._perform_reveal_service(ip, rule_data)

    def _get_matching_rules(self, path):
        active_rules = self.search([])
        rules = self.env['reveal.lead.rule']
        for rule in active_rules:
            try:
                if rule.regex_url:
                    if re.match(rule.regex_url, path, re.I | re.M):
                        rules += rule
                else:
                    rules += rule
            except Exception as e:
                _logger.error("Reveal Service: matching regex %s" % (e,))
        return rules

    def _get_data_for_server(self):
        rule_data = []
        for rule in self:
            data = {
                'rule_id': rule.id,
                'lead_for': rule.lead_for,
                'countries': rule.country_ids.mapped('code'),
                'company_size_min': rule.company_size_min,
                'company_size_max': rule.company_size_max,
                'industry_tags': rule.industry_tag_ids.mapped('name'),
            }
            if rule.lead_for == 'people':
                data.update({
                    'preferred_role': rule.preferred_role_id and rule.preferred_role_id.name or '',
                    'other_roles': rule.other_role_ids.mapped('name'),
                    'seniority': rule.seniority_id and rule.seniority_id.name or '',
                    'extra_contacts': rule.extra_contacts
                })
            rule_data.append(data)
        return rule_data

    def _perform_reveal_service(self, ip, rules):
        result = False
        account_token = self.env['iap.account'].get('reveal')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT)

        params = {
            'account_token': account_token.account_token,
            'ip': ip,
            'rules': rules
        }

        result = jsonrpc(endpoint, params=params)
        if result:
            self._create_lead(result, ip)

    def _create_lead(self, result, ip):
        rule = self.search([('id', '=', result['rule_id'])])

        # lead data from rule
        lead_data = {
            'type': rule.lead_type,
            'team_id': rule.team_id.id,
            'tag_ids': [(6, 0, rule.tag_ids.ids)],
            'priority': rule.priority,
            'user_id': rule.user_id.id,
            'stage_id': rule.stage_id.id,
            'reveal_ip': ip,
            'reveal_rule_id': rule.id,
            'referred': 'Website Visitor'
        }
        lead_data.update(self._lead_data_from_result(result, rule.suffix))
        lead = self.env['crm.lead'].create(lead_data)
        lead.message_post_with_view('reveal_client.lead_message_template', values=self._get_data_for_log_message(result))

    def _get_data_for_log_message(self, result):
        reveal_data = result['reveal_data']
        people_data = result.get('people_data')

        return {
            'twitter': reveal_data['twitter'],
            'facebook': reveal_data['facebook'],
            'linkedin': reveal_data['linkedin'],
            'crunchbase': reveal_data['crunchbase'],
            'timezone': reveal_data['timezone'],
            'timezone_link': reveal_data['timezone'].lower().replace('_','-'),
            'tech': ' , '.join(reveal_data['tech']),
            'people_data': people_data[1:]
        }

    def _lead_data_from_result(self, result, suffix):
        reveal_data = result['reveal_data']
        people_data = result.get('people_data')
        name = reveal_data['name']
        if suffix:
            name += ' - ' + suffix
        data = {
            'name': name,
            'iap_credits': result['credit'],
            'partner_name': reveal_data['name'],
            'phone': reveal_data['phone'],
            'website': reveal_data['domain'],
            'street': reveal_data['location'],
            'city': reveal_data['city'],
            'zip': reveal_data['postal_code'],
            'country_id': self._find_country_id(reveal_data['country_code']),
            'state_id': self._find_state_id(reveal_data),
            'description': self._get_lead_description(reveal_data),
        }
        if people_data:
            data.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['role'],
            })

        return data

    def _get_lead_description(self, reveal_data):

        description = ""

        print_rules = ['website_title','sector', 'legal_name', 'twitter_bio', 'twitter_followers', 'twitter_location']
        numbers = ['raised', 'market_cap', 'employees', 'estimated_annual_revenue']
        for key in print_rules:
            if reveal_data[key]:
                description += "%s : %s \n" % ( key.replace('_', ' ').title(), reveal_data[key])

        millnames = ['', ' K', ' M', ' B', 'T']
        def millify(n):
            try:
                n = float(n)
                millidx = max(0, min(len(millnames) - 1,int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))
                return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
            except Exception as e:
                return n

        for key in numbers:
            if reveal_data[key]:
                description += "%s : %s \n" % (key.replace('_', ' ').title(), millify(reveal_data[key]))

        return description


    def _find_country_id(self, country_code):
        return self.env['res.country'].search([['code', '=ilike', country_code]]).id

    def _find_state_id(self, data):
        country_id = self._find_country_id(data['country_code'])
        state_id = self.env['res.country.state'].search([['code', '=ilike', data['state_code']], ['country_id', '=', country_id]])
        if state_id:
            return state_id.id
        else:
            return self.env['res.country.state'].create({
                'country_id': country_id,
                'code': data['state_code'],
                'name': data['state_name']
            }).id

class IndustryTag(models.Model):
    """ Tags of Acquisition Rules """
    _name = 'reveal.industry.tag'
    _description = 'Industry Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]


class PeopleRole(models.Model):
    """ Roles for People Rules """
    _name = 'reveal.people.role'
    _description = 'People Role'

    name = fields.Char(string='Role Name', required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Role name already exists!"),
    ]

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for role in self:
            name = role.name.replace('_', ' ').title()
            result.append((role.id, name))
        return result

class PeopleSeniority(models.Model):
    """ Seniority for People Rules """
    _name = 'reveal.people.seniority'
    _description = 'People Seniority'

    name = fields.Char(string='Name', required=True, translate=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Name already exists!"),
    ]

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for seniority in self:
            name = seniority.name.replace('_', ' ').title()
            result.append((seniority.id, name))
        return result
