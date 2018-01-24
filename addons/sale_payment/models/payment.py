# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.multi
    def post(self):
        '''Sales orders are sent automatically upon the transaction is posted.
        if the option 'automatic_invoice' is enabled, an invoice is created for each sales orders and they are linked
        to the account.payment using the inherits.
        If not, the sales orders are posted without any further invoices.
        '''
        automatic_invoice = self.env['ir.config_parameter'].sudo().get_param('website_sale.automatic_invoice')
        for trans in self.filtered(lambda t: t.sale_order_ids):
            for so in trans.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent')):
                # Confirm the sales orders linked to the payment.
                so.action_confirm()

            trans.sale_order_ids._force_lines_to_invoice_policy_order()

            if not automatic_invoice:
                continue

            # Create invoices automatically.
            invoices = trans.sale_order_ids.action_invoice_create()
            trans.invoice_ids = [(6, 0, invoices)]
        return super(PaymentTransaction, self).post()

    @api.multi
    def mark_to_capture(self):
        # The sale orders are confirmed if the transaction are set to 'capture' directly.
        for trans in self.filtered(lambda t: not t.capture and t.acquirer_id.capture_manually):
            sales_orders = trans.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
            sales_orders.action_confirm()
        super(PaymentTransaction, self).mark_to_capture()

    @api.multi
    def mark_as_pending(self):
        # The quotations are sent for each remaining sale orders in state 'draft'.
        super(PaymentTransaction, self).mark_as_pending()
        for trans in self.filtered(lambda t: t.pending):
            sales_orders = trans.sale_order_ids.filtered(lambda so: so.state == 'draft')
            sales_orders.force_quotation_send()

    # --------------------------------------------------
    # Tools for payment
    # --------------------------------------------------

    def render_sale_button(self, order, return_url, submit_txt=None, render_values=None):
        values = {
            'return_url': return_url,
            'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
            'billing_partner_id': order.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)
        # Not very elegant to do that in this place but this is the only common place in each transaction
        # to log a message in the chatter.
        self._preprocess_payment_transaction()
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values=values,
        )
