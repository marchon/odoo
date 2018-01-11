# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        res = super(WizardMultiChartsAccounts, self)._create_bank_journals_from_o2m(company, acc_template_ref)

        # Search for installed acquirers modules
        acquirer_modules = self.env['ir.module.module'].search(
            [('name', 'like', 'payment_%'), ('state', '=', 'installed')])
        acquirer_names = [a.name.split('_')[1] for a in acquirer_modules]

        # Search for acquirers having no journal
        acquirers = self.env['payment.acquirer'].search(
            [('provider', 'in', acquirer_names), ('journal_id', '=', False), ('company_id', '=', self.company_id.id)])

        # Try to generate the missing journals
        return res + acquirers.try_loading_for_acquirer()
