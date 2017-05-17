# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tools import float_utils
from odoo.addons.stock_account.tests.test_valuation_reconciliation_common import ValuationReconciliationTestCase

class TestValuationReconciliation(ValuationReconciliationTestCase):

    def create_sale(self):
        rslt = self.env['sale.order'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_one.id,
            'order_line': [
                (0, 0, {
                    'name': self.test_product.name,
                    'product_id': self.test_product.id,
                    'qty_to_invoice': 1.0,
                    'product_uom': self.test_product.uom_po_id.id,
                    'price_unit': self.product_price_unit,
                })],
        })
        rslt.action_confirm()
        return rslt

    def create_invoice_for_so(self, sale_order):
        account_payable = self.env['account.account'].create({'code': 'X1111', 'name': 'Sale - Test Payable Account', 'user_type_id': self.env.ref('account.data_account_type_payable').id, 'reconcile': True})
        account_income = self.env['account.account'].create({'code': 'X1112', 'name': 'Sale - Test Account', 'user_type_id': self.env.ref('account.data_account_type_direct_costs').id})
        rslt = self.env['account.invoice'].create({
            'partner_id': self.test_partner.id,
            'reference_type': 'none',
            'currency_id': self.currency_two.id,
            'name': 'customer invoice',
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y') + '-12-22',
            'account_id': account_payable.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'origin': sale_order.name,
                'account_id': account_income.id,
                'price_unit': self.currency_one.compute(self.product_price_unit, self.currency_two, round=False),
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': self.test_product.uom_id.id,
                'product_id': self.test_product.id,
                'sale_line_ids': [(6, 0, [line.id for line in sale_order.order_line])],
            })],
        })

        sale_order.invoice_ids += rslt
        return rslt

    def check_reconciliation(self, invoice, sale_order):
        invoice_line = self.env['account.move.line'].search([('move_id','=',invoice.move_id.id), ('product_id','=',self.test_product.id), ('account_id','=',self.output_account.id)])
        self.assertEqual(len(invoice_line), 1, "Only one line should have been written by invoice in stock input account")
        self.assertNotEqual(float_utils.float_compare(invoice_line.amount_residual, invoice_line.credit, precision_digits=self.currency_one.decimal_places), 0, "The invoice's account move line should have been partly reconciled with stock valuation")

        valuation_line = self.env['stock.picking'].search([('sale_id','=',sale_order.id)]).move_lines.stock_account_valuation_account_move_ids.line_ids.filtered(lambda x: x.account_id == self.output_account)
        self.assertEqual(len(valuation_line), 1, "Only one line should have been written for stock valuation in stock input account")
        self.assertTrue(valuation_line.reconciled or invoice_line.reconciled, "The valuation and invoice line should have been reconciled together.")

        self.assertEqual(float_utils.float_compare(invoice_line.credit + invoice_line.amount_residual,valuation_line.debit - valuation_line.amount_residual,self.currency_one.decimal_places), 0 , "The reconciled amount of invoice move line should match the stock valuation line.")

    def test_shipment_invoice(self):
        """ Tests the case into which we send the goods to the customer before
        making the invoice
        """

        self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'qty': 42,
            'cost': 11,
        })

        sale_order = self.create_sale()
        sale_order.picking_ids.action_done()

        invoice = self.create_invoice_for_so(sale_order)
        self.currency_rate.rate = 9.87366352
        invoice.action_invoice_open()
        self.check_reconciliation(invoice, sale_order)

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then send
        the goods to our customer.
        """

        sale_order = self.create_sale()

        invoice = self.create_invoice_for_so(sale_order)
        self.currency_rate.rate = 0.974784
        invoice.action_invoice_open()

        sale_order.picking_ids.action_done()

        self.check_reconciliation(invoice, sale_order)

