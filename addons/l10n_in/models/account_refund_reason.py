# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceRefundReason(models.Model):

    _name = "account.invoice.refund.reason"

    code = fields.Char("Sequence Code", required=True)
    name = fields.Char("Name", required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The Sequence Code must be unique!')
    ]

    @api.multi
    def name_get(self):
        res = []
        for reason in self:
            name = '%s - %s' % (reason.code, reason.name)
            res.append((reason.id, name))
        return res
