# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    payment_ids_nbr = fields.Integer(string='# of Payments', compute='_compute_payment_ids_nbr')

    @api.depends('payment_ids')
    def _compute_payment_ids_nbr(self):
        for so in self:
            so.payment_ids_nbr = len(so.payment_ids)

    @api.multi
    def get_portal_transactions(self):
        return self.sudo().mapped('payment_ids.payment_transaction_ids')\
            .filtered(lambda trans: trans.state == 'posted' or (trans.state == 'draft' and trans.pending))

    @api.multi
    def get_portal_last_transaction(self):
        return self.sudo().payment_tx_id

    def action_view_payments(self):
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'target': 'current',
        }
        payment_ids = self.mapped('payment_ids')
        if len(payment_ids) == 1:
            action['res_id'] = payment_ids.ids[0]
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', payment_ids.ids)]
        return action
