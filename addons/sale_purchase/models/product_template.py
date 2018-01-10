# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from openerp.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_to_purchase = fields.Boolean("Create an RFQ", help="If checked, when confirming a Sale Order, this product will create a Purchase Order.")

    @api.onchange('type')
    def _onchange_product_type(self):
        if self.type != 'service':
            self.service_to_purchase = False

    @api.onchange('expense_policy')
    def _onchange_expense_policy(self):
        if self.expense_policy != 'no':
            self.service_to_purchase = False

    @api.constrains('type', 'service_to_purchase')
    def _check_type_service_to_purchase(self):
        for product in self:
            if product.type != 'service' and product.service_to_purchase:
                raise ValidationError(_("The product %s can not be a service creating an RFQ if its type is not a service.") % (product.name,))

    @api.constrains('expense_policy', 'service_to_purchase')
    def _check_expense_policy_service_to_purchase(self):
        for product in self:
            if product.expense_policy != 'no' and product.service_to_purchase:
                raise ValidationError(_("The product %s can not have a reinvoice policy and create an RFQ on sales order confirmation.") % (product.name,))
