# -*- coding: utf-8 -*-
import uuid
from odoo import api, fields, models, _

class SendOrderWizard(models.TransientModel):
    _name = 'snailmail.send.order.wizard'
    _description = 'Send Order Wizard'

    ink = fields.Selection([('BW', 'Black & White'), ('CL', 'Colour')], "Ink", default=lambda self: self.env.user.company_id.snailmail_ink)
    cost_estimation = fields.Boolean(help='Ask a confirmation with the amount of the order', default=lambda self: self.env.user.company_id.snailmail_cost_estimation)
    send_order_line_wizard_ids = fields.One2many('snailmail.send.order.line.wizard', 'snailmail_print_order_wizard', string='Lines')

    order_uuid = fields.Char(string='Order UUID', help='Id of the order, to send to partner server', default=lambda s: uuid.uuid4().hex)
    res_model = fields.Char('Resource Model')
    report_id = fields.Many2one('ir.actions.report', 'Report', domain=lambda self: [('model', '=', self.env.context.get('active_model'))])

    @api.onchange('ink', 'report_id')
    def _onchange_order_uuid(self):
        self.order_uuid = uuid.uuid4().hex

    @api.model
    def default_get(self, fields):
        result = super(SendOrderWizard, self).default_get(fields)

        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', False)
        result['res_model'] = active_model
        # generate line values
        if active_model and active_ids and 'send_order_line_wizard_ids' in fields:
            line_values = []
            for record in self.env[active_model].browse(active_ids):
                line_values.append({
                    'res_id': record.id,
                    'name': record.display_name,
                    'partner_id': record.partner_id.id if 'partner_id' in record else False,
                    'has_address': record.partner_id.has_address if 'partner_id' in record else False 
                })
            result['send_order_line_wizard_ids'] = [
                (0, 0, vals) for vals in line_values
            ]
        # add a default report
        if active_model and 'report_id' in fields:
            result['report_id'] = self.env['ir.actions.report'].search([('model', '=', active_model)], limit=1).id
        return result

    @api.multi
    def action_snailmail_print(self):
        self.env[self.res_model].action_snailmail_print(self, self.env.context.get('active_ids', []))

class SendOrderLineWizard(models.TransientModel):
    _name = 'snailmail.send.order.line.wizard'

    snailmail_print_order_wizard = fields.Many2one('snailmail.send.order.wizard', 'Send Order Wizard')
    res_id = fields.Integer('Resource ID', readonly=True)
    name = fields.Char('Document', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Recipient partner', readonly=True)
    has_address = fields.Boolean()
