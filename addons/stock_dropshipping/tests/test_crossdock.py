from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestCrossdock(TestStockDropshippingCommon):

    def test_00_crossdock(self):
        """ Test the Sales/Purchase order flow with cross dock."""

        # write a delivery step in 'pick_pack_ship'
        self.warehouse.delivery_steps = 'pick_pack_ship'

        # Creating Product
        self.product = self.Product.create({
            'name': "PCE",
            'list_price': 100.0,
            'standard_price': 70.0,
            'type': "product",
            'categ_id': self.category_all.id,
            'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner.id, 'min_qty': 2.0})]})

        # Creating Sale Order
        sale_order_crossdock = self._create_sale_order(
                                        partner_id=self.partner.id,
                                        product=self.product,
                                        product_qty=100,
                                        uom_id=self.uom_unit.id)

        # Check that crossdock route active or not.
        self.assertTrue(self.warehouse.crossdock_route_id.active, "Crossdock route should be active ...")
        # Set cross dock route on order line.
        sale_order_crossdock.order_line.write({'route_id': self.warehouse.crossdock_route_id.id})

        # Confirming Sale Order
        sale_order_crossdock.action_confirm()

        # Run Scheduler
        self.ProcurementOrder.run_scheduler()

        # Searching purchase Order by their partner.
        purchase_order = self.PurchaseOrder.search([('partner_id', '=', self.partner.id), ('state', '=', 'draft')])
        # Check purchase order created or not.
        self.assertTrue(purchase_order, 'No Purchase order!')
        # Confirming Purchase Order
        purchase_order.button_confirm()

    def test_01_procurement_exceptions(self):
        """ Test procurement exception when no supplier define on product with cross dock. """

        # write a delivery step in 'pick_pack_ship'
        self.warehouse.delivery_steps = 'pick_pack_ship'
        product_with_no_seller = self.Product.create({
            'name': 'product with no seller',
            'list_price': 20.0,
            'standard_price': 15.00,
            'categ_id': self.category_all.id})

        # Creating Sale Order
        sale_order_crossdock = self._create_sale_order(
                                        partner_id=self.partner.id,
                                        product=product_with_no_seller,
                                        product_qty=1,
                                        uom_id=self.uom_unit.id)
        # Set route on sale order line
        sale_order_crossdock.order_line.write({'route_id': self.warehouse.crossdock_route_id.id})
        # Confirm sale order
        sale_order_crossdock.action_confirm()
        # Run Procurement.
        self.ProcurementOrder.run_scheduler()
        # Procurement should be in exception state.
        procs = self.ProcurementOrder.search([('group_id', '=', sale_order_crossdock.procurement_group_id.id), ('state', '=', 'exception')])
        self.assertTrue(procs, 'No Procurement!')
        # Set the at least one supplier on the product.
        product_with_no_seller.write({'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner.id, 'min_qty': 2.0})]})
        # Run procurement again.
        procs.run()
        # Check the status changed there is no procurement order in exception any more from that procurement group
        procs = self.ProcurementOrder.search([('group_id.name', '=', sale_order_crossdock.name), ('state', '=', 'exception')])
        self.assertFalse(procs, 'Procurement should be in running state!')
        # Check a purchase quotation was created or not.
        procs = self.ProcurementOrder.search([('group_id.name', '=', sale_order_crossdock.name)])
        purchase_ids = procs.mapped('purchase_line_id').mapped('order_id').ids
        self.assertTrue(purchase_ids, 'No Purchase order!')
