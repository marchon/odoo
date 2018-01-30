# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.exceptions import AccessError
from odoo.tests import tagged


@tagged('post_install')
class TestAccessRights(TestSale):

    def setUp(self):
        super(TestAccessRights, self).setUp()
        self.partner1 = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
        })

    def test_access_rights_user(self):
        with self.assertRaises(AccessError):
            self.partner1.sudo(self.user).read({})

        with self.assertRaises(AccessError):
            self.partner1.sudo(self.user).write({'name': 'My Customer'})

        self.env = self.env(user=self.user)
        with self.assertRaises(AccessError):
            self.env['res.partner'].create({
                'name': 'Customer_1',
                'email': 'customer_1@test.com',
            })

        with self.assertRaises(AccessError):
            self.partner1.sudo(self.user).unlink()
