# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceRefundReason(models.Model):

    _name = "account.invoice.refund.reason"

    name = fields.Char("Name")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The refund reason must be unique!')
    ]
