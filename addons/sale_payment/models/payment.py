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
                old_state = so.state
                # Confirm the sales orders linked to the payment.
                so.action_confirm()
                # Log a "state has changed" notification on the sales orders chatters.
                so._log_transaction_so_message(old_state, trans)

            trans.sale_order_ids._force_lines_to_invoice_policy_order()

            if not automatic_invoice:
                continue

            # Create invoices automatically.
            invoice_ids = trans.sale_order_ids.action_invoice_create()
            if invoice_ids:
                for inv in self.env['account.invoice'].browse(invoice_ids):
                    # Log a "state has changed" notification on the invoices chatters.
                    inv._log_transaction_invoice_creation_message(trans)
            trans.invoice_ids = [(6, 0, invoice_ids)]
        return super(PaymentTransaction, self.filtered(lambda t: not t.capture)).post()

    @api.multi
    def mark_to_capture(self):
        # The sale orders are confirmed if the transaction are set to 'capture' directly.
        for trans in self.filtered(lambda t: not t.capture and t.acquirer_id.capture_manually):
            for so in trans.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent')):
                old_state = so.state
                so.action_confirm()
                so._log_transaction_so_message(old_state, trans)
        super(PaymentTransaction, self).mark_to_capture()

    @api.multi
    def mark_as_pending(self):
        # The quotations are sent for each remaining sale orders in state 'draft'.
        super(PaymentTransaction, self).mark_as_pending()
        for trans in self.filtered(lambda t: t.pending):
            for so in trans.sale_order_ids.filtered(lambda so: so.state == 'draft'):
                old_state = so.state
                so.force_quotation_send()
                so._log_transaction_so_message(old_state, trans)

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
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values=values,
        )
