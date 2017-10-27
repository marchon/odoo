# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_regime = fields.Boolean("Tax Regime", config_parameter='point_of_sale.tax_regime')
    tax_regime_selection = fields.Boolean("Tax Regime Selection value", config_parameter='point_of_sale.tax_regime_selection')
    fiscal_position_ids = fields.Many2many(related='company_id.fiscal_position_ids', relation='account.fiscal.position', string='Fiscal Positions', help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position', related='company_id.default_fiscal_position_id')
    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id')
    iface_tax_included = fields.Selection([('subtotal', 'Tax-Excluded Price'), ('total', 'Tax-Included Price')], related="company_id.iface_tax_included", required=True)
    use_pricelist = fields.Boolean("Use a pricelist.", config_parameter='point_of_sale.use_pricelist')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
                                          implied_group='product.group_sale_pricelist',
                                          help="""Allows to manage different prices based on rules per category of customers.
                    Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
                                          implied_group='product.group_pricelist_item')
    pricelist_id = fields.Many2one('product.pricelist', related='company_id.pricelist_id', string='Default Pricelist', required=True,
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    available_pricelist_ids = fields.Many2many('product.pricelist', related='company_id.available_pricelist_ids', string='Available Pricelists',
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    restrict_price_control = fields.Boolean(related='company_id.restrict_price_control', string='Restrict Price Modifications to Managers',
        help="Only users with Manager access rights for PoS app can modify the product prices on orders.")
    journal_ids = fields.Many2many(
        'account.journal', 'pos_config_journal_rel',
        'pos_config_id', 'journal_id', related='company_id.journal_ids', string='Available Payment Methods',
        domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    cash_control = fields.Boolean(related='company_id.cash_control', string='Cash Control', help="Check the amount of the cashbox at opening and closing.")
    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'default_pos_id', related='company_id.default_cashbox_lines_ids', string='Default Balance')
    iface_precompute_cash = fields.Boolean(related='company_id.iface_precompute_cash', string='Prefill Cash Payment',
        help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount.')
    module_pos_discount = fields.Boolean("Global Discounts", related='company_id.module_pos_discount')
    module_pos_loyalty = fields.Boolean(string="pos loyalty")
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment journal.")

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1)

    @api.onchange('use_pricelist')
    def _onchange_use_pricelist(self):
        """
        If the 'pricelist' box is unchecked, we reset the pricelist_id to stop
        using a pricelist for this posbox.
        """
        if not self.use_pricelist:
            self.pricelist_id = self._default_pricelist()
        else:
            self.update({
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })

    @api.onchange('tax_regime_selection')
    def _onchange_tax_regime_selection(self):
        if not self.tax_regime_selection:
            self.fiscal_position_ids = [(5, 0, 0)]

    @api.onchange('tax_regime')
    def _onchange_tax_regime(self):
        if not self.tax_regime:
            self.fiscal_position_id = False

    def _set_fiscal_position(self):
        for config in self:
            if config.tax_regime and config.fiscal_position_id.id not in config.fiscal_position_ids.ids:
                config.fiscal_position_ids = [(4, config.fiscal_position_id.id)]
            elif not config.tax_regime_selection and not config.tax_regime and config.fiscal_position_ids.ids:
                config.fiscal_position_ids = [(5, 0, 0)]

    @api.constrains('company_id', 'journal_ids')
    def _check_company_payment(self):
        if self.env['account.journal'].search_count([('id', 'in', self.journal_ids.ids), ('company_id', '!=', self.company_id.id)]):
            raise ValidationError(_("The company of a payment method is different than the one of point of sale"))

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.sudo()._set_fiscal_position()

    @api.constrains('journal_ids', 'available_pricelist_ids', 'pricelist_id')
    def _check_currencies(self):
        if self.pricelist_id not in self.available_pricelist_ids:
            raise ValidationError(_("The default pricelist must be included in the available pricelists."))
        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
        if any(self.journal_ids.mapped(lambda journal: journal.currency_id and journal.currency_id != self.currency_id)):
            raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))
