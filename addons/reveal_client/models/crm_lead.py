from odoo import fields, models


class Lead(models.Model):
    _inherit = 'crm.lead'

    reveal_ip = fields.Char(string='IP Address')
    iap_credits = fields.Integer(string='IAP Credits')
    reveal_rule_id = fields.Many2one('reveal.lead.rule', string='Reveal Rule ID')
