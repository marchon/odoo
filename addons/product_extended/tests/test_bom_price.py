# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.tools.float_utils import float_repr


class TestBom(common.TransactionCase):

    def _create_product(self, name, price):
        return self.Product.create({
            'name': name,
            'type': 'product',
            'standard_price': price,
        })

    def setUp(self):
        super(TestBom, self).setUp()
        self.Product = self.env['product.product']
        self.Bom = self.env['mrp.bom']
        self.Routing = self.env['mrp.routing']
        self.operation = self.env['mrp.routing.workcenter']

        # Products.
        self.dining_table = self._create_product('Dining Table', 1000)
        self.table_head = self._create_product('Table Head', 300)
        self.screw = self._create_product('Screw', 10)
        self.leg = self._create_product('Leg', 25)
        self.glass = self._create_product('Glass', 100)

        # Unit of Measure.
        self.unit = self.env.ref("product.product_uom_unit")
        self.dozen = self.env.ref("product.product_uom_dozen")

        # Bills Of Materials.
        # -----------------------------------------------------------------
        # Cost of BoM (Dining Table 1 Unit)
        # Component Cost = (Table Head   1 Unit * 468.75 = 468.75
        #                   Screw        5 Unit * 10     =  50
        #                   Leg          4 Unit * 25     = 100
        #                   Glass        1 Unit * 100    = 100
        #                                          Total = 718.75 (1 Unit)
        # -----------------------------------------------------------------

        self.bom_1 = self.Bom.create({
            'product_id': self.dining_table.id,
            'product_tmpl_id': self.dining_table.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': self.unit.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.table_head.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.screw.id, 'product_qty': 5}),
                (0, 0, {'product_id': self.leg.id, 'product_qty': 4}),
                (0, 0, {'product_id': self.glass.id, 'product_qty': 1})
            ]})

        # Table Head's components.
        self.plywood_sheet = self._create_product('Plywood Sheet', 200)
        self.bolt = self._create_product('Bolt', 10)
        self.colour = self._create_product('Colour', 100)
        self.corner_slide = self._create_product('Corner Slide', 25)

        # -----------------------------------------------------------------
        # Cost of BoM (Table Head 1 Dozen)
        # Component Cost = (Plywood sheet   12 Unit * 200 = 2400
        #                   Bolt            60 Unit * 10  =  600
        #                   Color           12 Unit * 100 = 1200
        #                   Corner Slide    57 Unit * 25  = 1425
        #                                           Total = 5625
        #                          1 Unit price (5625/12) =  468.75
        # -----------------------------------------------------------------
    
        self.bom_2 = self.Bom.create({
            'product_id': self.table_head.id,
            'product_tmpl_id': self.table_head.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': self.dozen.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.plywood_sheet.id, 'product_qty': 12}),
                (0, 0, {'product_id': self.bolt.id, 'product_qty': 60}),
                (0, 0, {'product_id': self.colour.id, 'product_qty': 12}),
                (0, 0, {'product_id': self.corner_slide.id, 'product_qty': 57})
            ]})

    def test_00_compute_price(self):
        """Total price of the product should be the Bill of Material 1 +
           Components' Bill of Material."""

        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.compute_price()
        self.assertEqual(self.dining_table.standard_price, 718.75, "After computing price from BoM price should be 718.75")

    def test_01_compute_price_operation_cost(self):
        # Compute Based on Routing.
        self.workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'resource_calendar_id': 1,
            'time_efficiency': 100,
            'capacity': 2,
            'oee_target': 100,
            'time_start': 0,
            'time_stop': 0,
            'costs_hour': 100,
        })

        self.routing_1 = self.Routing.create({
            'name': 'Assembly Furniture',
        })
        self.operation_1 = self.operation.create({
            'name': 'Cutting',
            'workcenter_id': self.workcenter_1.id,
            'routing_id': self.routing_1.id,
            'time_mode': 'manual',
            'time_cycle_manual': 20,
            'batch': 'no',
            'sequence': 1,
        })
        self.operation_2 = self.operation.create({
            'name': 'Drilling',
            'workcenter_id': self.workcenter_1.id,
            'routing_id': self.routing_1.id,
            'time_mode': 'manual',
            'time_cycle_manual': 25,
            'batch': 'no',
            'sequence': 2,
        })
        self.operation_3 = self.operation.create({
            'name': 'Fitting',
            'workcenter_id': self.workcenter_1.id,
            'routing_id': self.routing_1.id,
            'time_mode': 'manual',
            'time_cycle_manual': 30,
            'batch': 'no',
            'sequence': 3,
        })

        # -----------------------------------------------------------------
        # Dinning Table Operation Cost(1 Unit)
        # -----------------------------------------------------------------
        # As capacity of workcenter 2 operation cost calculate for 2 units
        # Cutting        (20 / 60) * 100 =  33.33
        # Drilling       (25 / 60) * 100 =  41.67
        # Fitting        (30 / 60) * 100 =  50.00
        # ----------------------------------------
        # Operation Cost  1 unit (125/2 capacity = 75 per unit
        # -----------------------------------------------------------------

        self.bom_1.routing_id = self.routing_1.id

        # --------------------------------------------------------------------------
        # Table Head Operation Cost (1 Dozen)
        # --------------------------------------------------------------------------
        # As capacity of workcenter 2 operation cost calculate for 2 dozens
        # Cutting        (20 / 60) * 100 =  33.33
        # Drilling       (25 / 60) * 100 =  41.67
        # Fitting        (30 / 60) * 100 =  50.00
        # ----------------------------------------
        # Operation Cost  1 dozen (125/2 capacity = 62.5 per dozen) and 5.21 1 Unit 
        # --------------------------------------------------------------------------

        self.bom_2.routing_id = self.routing_1.id

        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.compute_price()
        # Total cost of Dining Table = (718.75) + Total cost of operations (62.5 + 5.21) = 786.46
        self.assertEqual(float(float_repr(self.dining_table.standard_price, precision_digits=2)), 786.46, "After computing price from BoM price should be 786.46")
