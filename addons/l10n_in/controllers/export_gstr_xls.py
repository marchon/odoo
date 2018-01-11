# -*- coding: utf-8 -*-
import base64
import mimetypes
import os
import re
import io
import calendar
import datetime

from odoo.http import request

from odoo.tools.misc import str2bool, xlwt, file_open

from odoo import fields, http, _
from odoo.addons.web.controllers.main import content_disposition
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class ExportXLS(http.Controller):

    def export_xls(self, row, column, gst_type, datas):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet(gst_type)
        self.style_header = xlwt.easyxf('pattern: pattern solid, fore_colour light_blue; font: colour white, height 250; align: horiz center')
        self.style_header.font.bold = True
        self.style_header.borders.bottom = xlwt.Borders.MEDIUM
        self.style_header.borders.top = xlwt.Borders.MEDIUM
        self.style_header.borders.right = xlwt.Borders.MEDIUM
        self.style_header.borders.left = xlwt.Borders.MEDIUM
        worksheet.write(0, 0, _('Summary for %s') % str(gst_type).upper(), self.style_header)
        for row_index, value in enumerate(row):
            worksheet.write(1, row_index, value, self.style_header)
            worksheet.col(row_index).width = 8000
        for colm_index,  value in enumerate(column):
            style_header = xlwt.easyxf('pattern: pattern solid, fore_colour tan; font: height 250; align: horiz center')
            worksheet.write(3, colm_index, value, style_header)
            worksheet.col(colm_index).width = 8000
        for row_index, data in enumerate(datas):
            for i, y  in enumerate(data):
                worksheet.write(4+row_index, i, y)

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    def change_date_to_other_format(self, str_date):
        return str_date and fields.Date.from_string(str_date).strftime('%d-%b-%Y') or ''


    @http.route(['/xls/download/<string:month>/<string:year>/<string:gst_type>'], type='http', auth='public')
    def download_xls_report(self, month=None, year=None, gst_type=None, **post):
        invoice_data = []
        _, num_days = calendar.monthrange(int(year), int(month))
        first_day = datetime.date(int(year), int(month), 1)
        last_day = datetime.date(int(year), int(month), num_days)
        cgst_group_id = request.env.ref('l10n_in.cgst_tag_tax').id
        sgst_group_id = request.env.ref('l10n_in.sgst_tag_tax').id
        igst_group_id = request.env.ref('l10n_in.igst_tag_tax').id
        #Get value from account settings
        ICPSudo = request.env['ir.config_parameter'].sudo()
        b2cs_amount = ICPSudo.get_param('l10n_in.l10n_in_b2cs_max') or 250000
        invoice_data = []
        domain = [('date_invoice', '>' , first_day), ('date_invoice', '<', last_day), ('state', 'in', ['open', 'paid'])]
        if gst_type == 'b2b':
            journal_id = request.env['account.journal']._search([('code','=','INV')])
            row_data = ['No. of Recipients', 'No. of Invoices', '', 'Total Invoice Value', '', '', '', '', '', 'Total Taxable Value', 'Total Cess']
            column_data = ['GSTIN/UIN of Recipient', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Place Of Supply', 'Reverse Charge', 'Invoice Type',
            'E-Commerce GSTIN', 'Rate', 'Taxable Value', 'Cess Amount']
            domain += [('type', '=', 'out_invoice'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append((invoice.partner_id.vat or '', invoice.number, self.change_date_to_other_format(invoice.date_invoice), invoice.amount_total, "%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), 'N',
                        'Regular', '', rate, value['base_amount'], 0))

        if gst_type == 'b2cl':
            journal_id = request.env['account.journal']._search([('code','=','RETIN')])
            row_data = ['No. of Invoices', '', 'Total Inv Value', '', '', 'Total Taxable Value', 'Total Cess', '']
            column_data = ['Invoice Number', 'Invoice Date', 'Invoice Value', 'Place Of Supply', 'Rate', 'Taxable Value', 'Cess Amount', 'E-Commerce GSTIN']
            domain += [('amount_total', '>', b2cs_amount),('type', '=', 'out_invoice'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append((invoice.number, self.change_date_to_other_format(invoice.date_invoice), invoice.amount_total, "%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), rate, value['base_amount'], '',''))

        if gst_type == 'b2cs':
            journal_id = request.env['account.journal']._search([('code','=','RETIN')])
            row_data = ['', '', '', 'Total Taxable  Value', 'Total Cess', '']
            column_data = ['Type', 'Place Of Supply', 'Rate', 'Taxable Value', 'Cess Amount', 'E-Commerce GSTIN']
            domain += [('amount_total', '<=', b2cs_amount),('type', '=', 'out_invoice'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append(('', "%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), rate, value['base_amount'], '', ''))

        if gst_type == 'cdnr':
            journal_id = request.env['account.journal']._search([('code','=','INV')])
            row_data = ['No. of Recipients', 'No. of Invoices', '', 'No. of Notes/Vouchers', '', '', '', '','', 'Total Note/Refund Voucher Value', 'Total Taxable Value', 'Total Cess', '']
            column_data = ['GSTIN/UIN of Recipient', 'Invoice/Advance Receipt Number', 'Invoice/Advance Receipt date', 'Note/Refund Voucher Number', 'Note/Refund Voucher date', 'Document Type', 'Reason For Issuing document',
            'Place Of Supply', 'Note/Refund Voucher Value', 'Rate', 'Taxable Value', 'Cess Amount', 'Pre GST']
            domain += [('type', '=', 'out_refund'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append((invoice.partner_id.vat or '', invoice.number, self.change_date_to_other_format(invoice.date_invoice), invoice.refund_invoice_id.number or '', self.change_date_to_other_format(invoice.refund_invoice_id.date_invoice), 'C', invoice.refund_reason_id.name or '', "%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), invoice.amount_total, rate, value['base_amount'], '', ''))

        if gst_type == 'cdnur':
            journal_id = request.env['account.journal']._search([('code','in',['RETIN','EXPINV'])])
            row_data = ['', 'No. of Notes/Vouchers', '', '', 'No. of Invoices', '', '', '', 'Total Note Value', 'Total Taxable Value', 'Total Cess', '']
            column_data = ['UR Type', 'Note/Refund Voucher Number', 'Note/Refund Voucher date', 'Document Type', 'Invoice/Advance Receipt Number', 'Invoice/Advance Receipt date', 'Reason For Issuing document',
            'Place Of Supply', 'Note/Refund Voucher Value', 'Rate', 'Taxable Value', 'Cess Amount', 'Pre GST']
            domain += [('type', '=', 'out_refund'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                ur_type = 'B2CL'
                if invoice.fiscal_position_id.id == fiscal_position_export_id:
                    ur_type = invoice.tax_line_ids and 'WPAY' or 'WOPAY'
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append((ur_type, invoice.number,self.change_date_to_other_format(invoice.date_invoice),'C', invoice.refund_invoice_id.number, self.change_date_to_other_format(invoice.refund_invoice_id.date_invoice), invoice.refund_reason_id.name or '', invoice.name, "%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), invoice.amount_total, rate, value['base_amount'], '', ''))

        if gst_type == 'exp':
            journal_id = request.env['account.journal']._search([('code','=','EXPINV')])
            row_data = ['', 'No. of Invoices', '', 'Total Invoice Value', '', 'No. of Shipping Bill', '', '', 'Total Taxable Value']
            column_data = ['Export Type', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Port Code', 'Shipping Bill Number', 'Shipping Bill Date', 'Rate', 'Taxable Value']
            domain += [('type', '=', 'out_invoice'),('journal_id','in',journal_id)]
            invoices = request.env['account.invoice'].search(domain)
            for invoice in invoices:
                for rate, value in invoice._invoice_line_group_tax_values().items():
                    invoice_data.append((invoice.tax_line_ids and 'WPAY' or 'WOPAY', invoice.number, self.change_date_to_other_format(invoice.date_invoice), invoice.amount_total_signed, '', '', '', rate, value['base_amount']))

        if gst_type == 'at':
            row_data = ['', '', 'Total Advance Received', 'Total Cess']
            column_data = ['Place Of Supply', 'Rate', 'Gross Advance Received', 'Cess Amount']
            #product_id = request.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            payments = request.env['account.payment'].search([('payment_date', '>', first_day),
                                                              ('payment_date', '<', last_day),
                                                              ('state', '=', 'posted'), ('payment_type', '=', 'inbound')])
            group_data = {}
            for payment in payments:
                advance_amount = payment.amount
                for invoice in payment.invoice_ids.filtered(lambda i: i.date_invoice < last_day.strftime(DEFAULT_SERVER_DATE_FORMAT)):
                    for invoice_payment in invoice._get_payments_vals():
                        if invoice_payment['account_payment_id'] == payment.id:
                           advance_amount -= invoice_payment['amount']
                if advance_amount > 0.00:
                    group_data.setdefault("%s-%s" %(invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name),[]).append(advance_amount)
            for key, value in group_data.items():
                invoice_data.append((key,'',sum(value),''))
                #I try it with account.move.line but can't get appropriate data
                # use_amount = []
            #     for payment_move_line in payment.move_line_ids.filtered(lambda m: m.account_id.reconcile):
            #         payment_reconcile_moves = request.env['account.move.line'].browse([r.debit_move_id.id for r in payment_move_line.matched_debit_ids] if payment_move_line.credit > 0 else [r.credit_move_id.id for r in payment_move_line.matched_credit_ids])
            #         for payment_reconcile_move in payment_reconcile_moves.filtered(lambda m: m.date_maturity < last_day.strftime(DEFAULT_SERVER_DATE_FORMAT)):
            #             use_amount.append(payment_reconcile_move.debit)
            #             print("Payment",data_test)
            #     data_test.setdefault(payment.partner_id.name, []).append({'advance_amount':advance_amount,'use_amount':use_amount})
            # print("Payment",data_test)

                #invoice_data.append(("%s-%s" % (invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name), invoice.amount_total, ''))

        if gst_type == 'atadj':
            row_data = ['', '', 'Total Advance Adjusted', 'Total Cess']
            column_data = ['Place Of Supply', 'Rate', 'Gross Advance Adjusted', 'Cess Amount']
            group_data = {}
            #product_id = request.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            invoices = request.env['account.invoice'].search(domain_common)
            for invoice in invoices:
                for invoice_payment in invoice._get_payments_vals():
                    if invoice_payment['date'] < invoice.date_invoice and invoice_payment['date'] < first_day.strftime(DEFAULT_SERVER_DATE_FORMAT):
                        group_data.setdefault("%s-%s" %(invoice.partner_id.state_id.l10n_in_tin, invoice.partner_id.state_id.name),[]).append(invoice_payment['amount'])
            for key, value in group_data.items():
                invoice_data.append((key,'',sum(value),''))

        if gst_type == 'exemp':
            row_data = ['', 'Total Nil Rated Supplies', 'Total Exempted Supplies', 'Total Non-GST Supplies']
            column_data = ['Description', 'Nil Rated Supplies', 'Exempted (other than nil rated/non GST supply )', 'Non-GST supplies']

        if gst_type == 'hsn':
            row_data = ['No. of HSN', '', '', '', 'Total Value', 'Total Taxable Value', 'Total Integrated Tax', 'Total Central Tax', 'Total State/UT Tax', 'Total Cess']
            column_data = ['HSN', 'Description', 'UQC', 'Total Quantity', 'Total Value', 'Taxable Value', 'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount']
            group_data = {}
            invoices = request.env['account.invoice'].search(domain_common + [('type','=','out_invoice')])
            for invoice in invoices:
                tax_values = invoice._invoice_line_tax_values()
                for invoice_line in invoice.invoice_line_ids:
                    igst = sgst = cgst = 0
                    for tax_value in tax_values[invoice_line.id]:
                        if igst_group_id in tax_value['tag_ids']:
                            igst += tax_value['amount']
                        if cgst_group_id in tax_value['tag_ids']:
                            cgst += tax_value['amount']
                        if sgst_group_id in tax_value['tag_ids']:
                            sgst += tax_value['amount']
                    group_key = (invoice_line.product_id.l10n_in_hsn_code or'' , invoice_line.product_id.l10n_in_hsn_description or '', invoice_line.uom_id.name or '')
                    group_data.setdefault(group_key,[]).append([invoice_line.quantity, invoice_line.price_total, invoice_line.price_subtotal_signed, igst, cgst, sgst,''])
            for key, values in group_data.items():
                description = ''
                total_quantity = total_value = taxable_value = igst = sgst = cgst = 0
                for value in values:
                    total_quantity += value[0]
                    total_value += value[1]
                    taxable_value += value[2]
                    igst += value[3]
                    sgst += value[4]
                    cgst += value[5]
                invoice_data.append((key[0], key[1], key[2], total_quantity, total_value, taxable_value, igst, sgst, cgst,''))

        if gst_type == 'docs':
            row_data = ['', '', '', 'Total Number', 'Total Cancelled']
            column_data = ['Nature  of Document', 'Sr. No. From', 'Sr. No. To', 'Total Number', 'Cancelled']

        return http.request.make_response(self.export_xls(row_data, column_data, gst_type, invoice_data),
            headers=[('Content-Disposition',
                            content_disposition("GSTR-%s.xls"%(gst_type.upper()))),
                     ('Content-Type', 'application/vnd.ms-excel')],
            cookies={'fileToken': bytearray()})
