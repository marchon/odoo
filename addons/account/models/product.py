# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account", oldname="property_account_income_categ",
        domain=[('deprecated', '=', False)],
        help="This account will be used when validating a customer invoice.")
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account", oldname="property_account_expense_categ",
        domain=[('deprecated', '=', False)],
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")
    property_account_income_refund_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Refund Account", domain=[('deprecated', '=', False)],
        help="This account will be used by default on the customer credit notes if no income refund account is set on the product")

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.user.company_id.account_sale_tax_id)
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes',
        domain=[('type_tax_use', '=', 'purchase')], default=lambda self: self.env.user.company_id.account_purchase_tax_id)
    property_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account", oldname="property_account_income",
        domain=[('deprecated', '=', False)],
        help="Keep this field empty to use the default value from the product category.")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account", oldname="property_account_expense",
        domain=[('deprecated', '=', False)],
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation. If the field is empty, it uses the one defined in the product category.")
    property_account_income_refund_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Refund Account", domain=[('deprecated', '=', False)],
        help="This account will be used by default on the customer credit notes")

    @api.multi
    def write(self, vals):
        #TODO: really? i don't see the reason we'd need that constraint..
        check = self.ids and 'uom_po_id' in vals
        if check:
            self._cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(self.ids)])
            uoms = dict(self._cr.fetchall())
        res = super(ProductTemplate, self).write(vals)
        if check:
            self._cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(self.ids)])
            if dict(self._cr.fetchall()) != uoms:
                products = self.env['product.product'].search([('product_tmpl_id', 'in', self.ids)])
                if self.env['account.move.line'].search_count([('product_id', 'in', products.ids)]):
                    raise UserError(_('You can not change the unit of measure of a product that has been already used in an account journal item. If you need to change the unit of measure, you may deactivate this product.'))
        return res

    @api.multi
    def _get_product_accounts(self):
        income_account = self.property_account_income_id or self.categ_id.property_account_income_categ_id
        income_refund_account = self.property_account_income_refund_id or self.categ_id.property_account_income_refund_categ_id
        expense_account = self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        return {
            'income': income_account,
            'income_refund': income_refund_account or income_account,
            'expense': expense_account
        }

    @api.multi
    def _get_asset_accounts(self):
        res = {}
        res['stock_input'] = False
        res['stock_output'] = False
        return res

    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        accounts = self._get_product_accounts()
        if not fiscal_pos:
            fiscal_pos = self.env['account.fiscal.position']
        return fiscal_pos.map_accounts(accounts)
