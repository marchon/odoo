# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions', help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.')
    default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    iface_tax_included = fields.Selection([('subtotal', 'Tax-Excluded Price'), ('total', 'Tax-Included Price')], default='subtotal', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist',
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    available_pricelist_ids = fields.Many2many('product.pricelist', string='Available Pricelists',
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    restrict_price_control = fields.Boolean(string='Restrict Price Modifications to Managers',
        help="Only users with Manager access rights for PoS app can modify the product prices on orders.")
    journal_ids = fields.Many2many(
        'account.journal', 'pos_config_journal_rel',
        'pos_config_id', 'journal_id', string='Available Payment Methods',
        domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    cash_control = fields.Boolean(string='Cash Control', help="Check the amount of the cashbox at opening and closing.")
    default_cashbox_lines_ids = fields.One2many('account.cashbox.line', 'default_pos_id', string='Default Balance')
    iface_precompute_cash = fields.Boolean(string='Prefill Cash Payment',
        help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount.')
    module_pos_discount = fields.Boolean("Global Discounts")
