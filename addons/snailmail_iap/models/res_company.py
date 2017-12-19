# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import os
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = "res.company"
    
    snailmail_ink = fields.Selection([('BW', 'Black & White'), ('CL', 'Colour')], "Ink", default='BW')
    snailmail_cost_estimation = fields.Boolean(string='Ask for confirmation', default=True)
