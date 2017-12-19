# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    snailmail_ink = fields.Selection(related='company_id.snailmail_ink')
    snailmail_cost_estimation = fields.Boolean(related='company_id.snailmail_cost_estimation')
