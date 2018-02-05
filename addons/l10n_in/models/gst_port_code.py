# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class GstPortCode(models.Model):
    _name = 'gst.port.code'

    sequence = fields.Integer(default=1)
    port_code = fields.Char(string = "Port Code")
    port_name = fields.Char(string = "Port")
    state_id = fields.Many2one('res.country.state', string="State")
    detail = fields.Text(string = "Port Code Details")
