# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.exceptions import UserError, AccessError

from .test_sale_common import TestCommonSaleNoChart
from odoo.tests import Form


class TestSaleOrder(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleOrder, cls).setUpClass()

        # set up users
        cls.setUpUsers()
        group_salemanager = cls.env.ref('sales_team.group_sale_manager')
        group_salesman = cls.env.ref('sales_team.group_sale_salesman')
        cls.user_manager.write({'groups_id': [(6, 0, [group_salemanager.id])]})
        cls.user_employee.write({'groups_id': [(6, 0, [group_salesman.id])]})

        # set up accounts and products and journals
        cls.setUpAdditionalAccounts()
        cls.setUpClassicProducts()
        cls.setUpAccountJournal()

        # create a generic Sale Order with all classical products
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': cls.product_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': cls.service_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': cls.service_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = cls.env['sale.order.line'].create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': cls.product_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        Invoice = self.env['account.invoice']
        self.sale_order.order_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])

        self.assertEqual(self.sale_order.amount_total, sum([2 * p.list_price for p in self.product_map.values()]), 'Sale: total amount is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)
        # send quotation
        self.sale_order.force_quotation_send()
        self.assertTrue(self.sale_order.state == 'sent', 'Sale: state after sending is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        inv_id = self.sale_order.action_invoice_create()
        invoice = Invoice.browse(inv_id)
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(invoice.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for p in self.product_map.values()]), 'Sale: invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 1, 'Sale: invoice is missing')
        self.sale_order.order_line._compute_product_updatable()
        self.assertFalse(self.sale_order.order_line[0].product_updatable)

        # deliver lines except 'time and material' then invoice again
        for line in self.sale_order.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy == 'no' else 0
        self.assertTrue(self.sale_order.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        inv_id = self.sale_order.action_invoice_create()
        invoice2 = Invoice.browse(inv_id)
        self.assertEqual(len(invoice2.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(invoice2.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for p in self.product_map.values()]), 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 2, 'Sale: invoice is missing')

        # go over the sold quantity
        self.sol_serv_order.write({'qty_delivered': 10})
        self.assertTrue(self.sale_order.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        self.sol_serv_order.write({'product_uom_qty': 10})

        inv_id = self.sale_order.action_invoice_create()
        invoice3 = Invoice.browse(inv_id)
        self.assertEqual(len(invoice3.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(invoice3.amount_total, 8 * self.product_map['serv_order'].list_price, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_unlink_cancel(self):
        """ Test deleting and cancelling sales orders depending on their state and on the user's rights """
        # SO in state 'draft' can be deleted
        so_copy = self.sale_order.copy()
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user_employee).unlink()
        self.assertTrue(so_copy.sudo(self.user_manager).unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user_employee).unlink()
        self.assertTrue(so_copy.sudo(self.user_manager).unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            self.sale_order.sudo(self.user_manager).unlink()

        self.sale_order.action_done()
        self.assertTrue(self.sale_order.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            self.sale_order.sudo(self.user_manager).unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
        # force the pricelist to have the same currency as the company
        self.pricelist_usd.currency_id = self.env.ref('base.main_company').currency_id

        serv_cost = self.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 160,
            'list_price': 180,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'PROD_COST',
            'service_type': 'manual',
        })
        prod_gap = self.service_order
        so = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.pricelist_usd.id,
        })
        so.action_confirm()
        so._create_analytic_account()

        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'STPJ', 'type': 'purchase', 'company_id': company.id})
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'partner_id': self.partner_customer_usd.id,
            'invoice_line_ids': [(0, 0, {'name': serv_cost.name, 'product_id': serv_cost.id, 'quantity': 2, 'uom_id': serv_cost.uom_id.id, 'price_unit': serv_cost.standard_price, 'account_analytic_id': so.analytic_account_id.id, 'account_id': self.account_income.id})],
            'account_id': self.account_payable.id,
            'journal_id': journal.id,
            'currency_id': company.currency_id.id,
        }
        inv = self.env['account.invoice'].create(invoice_vals)
        inv.action_invoice_open()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertEquals((sol.price_unit, sol.qty_delivered, sol.product_uom_qty, sol.qty_invoiced), (160, 2, 0, 0), 'Sale: line is wrong after confirming vendor invoice')

    def test_sale_with_pricelist_multi_price_per_product(self):
        """ Test pricelist apply or not on order line's products when pricelist on SO """
        # create pricelist
        pricelist = Form(self.env['product.pricelist'])
        pricelist.name = 'Pricelist A'
        pricelist.discount_policy = 'with_discount'
        with pricelist.item_ids.new() as item:
            item.applied_on = '1_product'
            item.product_tmpl_id = self.product_order.product_tmpl_id
            item.compute_price = 'percentage'
            item.percent_price = 10
        with pricelist.item_ids.new() as item:
            item.applied_on = '1_product'
            item.product_tmpl_id = self.service_deliver.product_tmpl_id
            item.compute_price = 'percentage'
            item.percent_price = 20
        pricelist_a = pricelist.save()

        pricelist = Form(self.env['product.pricelist'])
        pricelist.name = 'Pricelist B'
        pricelist.discount_policy = 'without_discount'
        with pricelist.item_ids.new() as item:
            item.applied_on = '1_product'
            item.product_tmpl_id = self.service_order.product_tmpl_id
            item.compute_price = 'percentage'
            item.percent_price = 20
        with pricelist.item_ids.new() as item:
            item.applied_on = '1_product'
            item.product_tmpl_id = self.product_deliver.product_tmpl_id
            item.compute_price = 'percentage'
            item.percent_price = 10
        pricelist_b = pricelist.save()
        # create sale order with pricelist
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.partner_customer_usd
        order_form.pricelist_id = pricelist_a
        with order_form.order_line.new() as line:
            line.product_id = self.product_order
        with order_form.order_line.new() as line:
            line.product_id = self.service_deliver
        with order_form.order_line.new() as line:
            line.product_id = self.service_order
        with order_form.order_line.new() as line:
            line.product_id = self.product_deliver

        order = order_form.save()

        # check only pricelist of sale order should be applied on products of sale order line
        for line in order.order_line:
            if order.pricelist_id in line.product_id.item_ids.mapped('pricelist_id'):
                for i in order.pricelist_id.item_ids:
                    if i.product_tmpl_id == line.product_id.product_tmpl_id:
                        price = i.percent_price
                self.assertEquals(price, (line.product_id.list_price - line.price_unit)/line.product_id.list_price*100, 'Pricelist A should be applied on product')
            else:
                self.assertEquals(line.price_unit, line.product_id.list_price, 'Pricelist should not be applied on product.')

    def test_sale_with_pricelist_formulas(self):
        """ Test sale order with a pricelist which one have compute price formula"""
        pricelist = Form(self.env['product.pricelist'])
        pricelist.name = 'Pricelist A'
        pricelist.discount_policy = 'without_discount'
        with pricelist.item_ids.new() as item:
            item.applied_on = '2_product_category'
            item.categ_id = self.product_category
            item.compute_price = 'formula'
            item.price_discount = 15
        pricelist_a = pricelist.save()

        pricelist = Form(self.env['product.pricelist'])
        pricelist.name = 'Pricelist B'
        pricelist.discount_policy = 'with_discount'
        with pricelist.item_ids.new() as item:
            item.applied_on = '3_global'
            item.compute_price = 'percentage'
            item.price_discount = 10
        pricelist_b = pricelist.save()

        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.partner_customer_usd
        order_form.pricelist_id = pricelist_a
        with order_form.order_line.new() as line:
            line.product_id = self.product_order
        with order_form.order_line.new() as line:
            line.product_id = self.service_deliver

        order = order_form.save()
