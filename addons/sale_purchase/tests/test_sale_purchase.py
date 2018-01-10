# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart


class TestSalePurchaseOrder(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSalePurchaseOrder, cls).setUpClass()

        # set up users
        cls.setUpUsers()
        group_salemanager = cls.env.ref('sales_team.group_sale_manager')
        group_salesman = cls.env.ref('sales_team.group_sale_salesman')
        cls.user_manager.write({'groups_id': [(6, 0, [group_salemanager.id])]})
        cls.user_employee.write({'groups_id': [(6, 0, [group_salesman.id])]})

        # set up accounts and products and journals
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

        # create a pricelist
        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': 'USD pricelist',
            'active': True,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.user.company_id.id,
        })

        # create product
        cls.service_product = cls.env['product.product'].create({
            'name': "Service Outsourced",
            'standard_price': 50.0,
            'list_price': 60.0,
            'type': 'service',
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'SERV_DEL',
            'service_type': 'manual',
            'taxes_id': False,
        })
        # TODO JEM: create supplier info !!

        # create a generic Sale Order with all classical products
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol_service_deliver = cls.env['sale.order.line'].create({
            'name': cls.service_product.name,
            'product_id': cls.service_product.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_product.uom_id.id,
            'price_unit': cls.service_product.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_create_purchase(self):
        """ Confirming a SO with a service that should create a PO """
        pass

    def test_access_right(self):
        """ Check a saleperson (only) can generate a PO and a PO user can not confirm a SO """
        pass

    def test_uom_conversion(self):
        """ Test generated PO use the right UoM according to product configuration """
        pass

    def test_no_supplier(self):
        """ Test confirming SO with product with no supplier raise Error """
        pass
