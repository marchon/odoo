# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CountryState(models.Model):
    _inherit = 'res.country.state'

    l10n_in_tin = fields.Char('TIN Number', size=2, help="TIN number-first two digits")

    @api.multi
    def tin_and_name(self):
        if not self.ids:
            return ''
        self.ensure_one()
        return self.l10n_in_tin and "%s-%s"%(self.l10n_in_tin, self.name) or ''
