# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.addons.iap import jsonrpc, InsufficientCreditError
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import time
import base64
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'http://partner.odoo:8069'
RESPONSE_COST = 1
RESPONSE_SEND = 2

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_send(self):
        """
        Open a wizard with options to send the invoices (by postal mail or email)
        """
        return {
            'name': _('Send'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'snailmail.send.order.wizard',
            'target': 'new'
        }

    def _log_postal_mail(self, order_token):
        """
        Log the sending in the mail_thread of the invoices
        """
        for record in self:
            msg = _('Invoice sent by Postal mail')
            msg += '<ul><li>' + _('Date: ') + fields.datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) + '</li>'
            msg += '<li>' + _('Order ID: ') + order_token + '</li></ul>'
            record.message_post(body=msg)
        return True

    def _create_params(self, report_id):
        """
        Create a dictionnary with parameters of the invoice (address, res_id and the pdf)
        """
        return {
            'address': {
                'name': self.partner_id.name,
                'street': self.partner_id.street,
                'street2': self.partner_id.street2,
                'zip': self.partner_id.zip,
                'state': self.partner_id.state_id.name if self.partner_id.state_id else False,
                'city': self.partner_id.city,
                'country': self.partner_id.country_id.code
            },
            'res_id': self.id,
            'pdf': base64.b64encode(report_id.render_qweb_pdf(self.id)[0])
        }

    def _snailmail_check_exist(self, endpoint, account_token, order_uuid):
        """
        Return true if the order_uuid exist in the partner's database, false otherwise
        """
        params = {
            'account_token': account_token,
            'order_token': order_uuid
        }
        return jsonrpc(endpoint + '/exist', params=params)

    def _snailmail_import_documents(self, endpoint, account_token, invoices, ids):
        """
        Import all the documents to partner's server. Return true if all is ok, false otherwise
        """
        all_invoices = self.env[invoices.res_model].browse(ids)
        documents = [inv._create_params(invoices.report_id) for inv in all_invoices]
        params = {
            'account_token': account_token,
            'order_token': invoices.order_uuid,
            'options': {
                'color': invoices.ink
            },
            'documents': documents
        }
        return jsonrpc(endpoint + '/import', params=params)

    @api.model
    def action_snailmail_print(self, invoices, ids):
        endpoint = self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', DEFAULT_ENDPOINT)
        user_token = self.env['iap.account'].get('snailmail')

        if not self._snailmail_check_exist(endpoint, user_token.account_token, invoices.order_uuid):
            # The order doesn't exist, we have to send all the invoices
            if not self._snailmail_import_documents(endpoint, user_token.account_token, invoices, ids):
                raise UserError(_('Error during the process, please contact the author of the app.'))
        
        params = {
            'account_token': user_token.account_token,
            'order_token': invoices.order_uuid,
            'to_print': not invoices.cost_estimation
        }
        response = jsonrpc(endpoint + '/print', params=params)
        if not self._validate_snailmail_response(response):
            raise UserError(_('Error during the process, please contact the author of the app.\nOrder token: %s') % invoices.order_uuid)
        if response['res_code'] == RESPONSE_COST:
            #TODO Open a popup with amount and Ok or Cancel
            return True

        if response['res_code'] == RESPONSE_SEND:
            for record in self.env['account.invoice'].browse(response['res_ids']):
                record._log_postal_mail(response['order_token'])
            # if not response['ok']:
            #     print("Open new send infos")
            #     return {
            #         'type': 'ir.actions.act_window',
            #         'res_model': 'payment.transaction',
            #         'target': 'new'
            #     }
            # for record in self.env['account.invoice'].browse(response['not_sent']):

        return True

    def _validate_snailmail_response(self, response):
        if 'res_code' not in response:
            return False
        if response['res_code'] == RESPONSE_COST: #Estimation
            if 'total_cost' not in response:
                return False
            return True
        if response['res_code'] == RESPONSE_SEND: #Print
            if 'order_token' not in response:
                return False
            if 'not_sent' not in response:
                return False
            if 'res_ids' not in response:
                return False
            return True
        return False

