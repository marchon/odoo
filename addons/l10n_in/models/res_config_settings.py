# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_in_b2cs_max = fields.Float(string="B2CS Max Value", default=250000, config_parameter='l10n_in.l10n_in_b2cs_max')
