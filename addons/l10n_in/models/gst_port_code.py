# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class GstPortCode(models.Model):
    _name = 'gst.port.code'

    sequence = fields.Integer(default=1)
    code = fields.Char(string = "Port Code", required=True)
    name = fields.Char(string = "Port", required=True)
    state_id = fields.Many2one('res.country.state', string="State")
    detail = fields.Text(string = "Port Code Details")

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The Port Code must be unique!')
    ]

    @api.multi
    def name_get(self):
        res = []
        for port_code in self:
            name = '%s - %s' % (port_code.code, port_code.name)
            res.append((port_code.id, name))
        return res
