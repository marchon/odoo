# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    refund_reason_id = fields.Many2one("account.invoice.refund.reason", string="Selected Reason")
    port_code_id = fields.Many2one("gst.port.code", string="Port Code")

    def _get_printed_report_name(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'IN':
            return super(AccountInvoice, self)._get_printed_report_name()
        return self.type == 'out_invoice' and self.state == 'draft' and _('Draft %s') % (self.journal_id.name) or \
            self.type == 'out_invoice' and self.state in ('open','paid') and '%s - %s' % (self.journal_id.name, self.number) or \
            self.type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
            self.type == 'out_refund' and _('Credit Note - %s') % (self.number) or \
            self.type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
            self.type == 'in_invoice' and self.state in ('open','paid') and _('Vendor Bill - %s') % (self.number) or \
            self.type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
            self.type == 'in_refund' and _('Vendor Credit Note - %s') % (self.number)

    @api.multi
    def _invoice_line_tax_values(self):
        self.ensure_one()
        tax_datas = {}
        TAX = self.env['account.tax']

        for line in self.mapped('invoice_line_ids'):
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)['taxes']
            for tax_line in tax_lines:
                tax_line['tag_ids'] = TAX.browse(tax_line['id']).tag_ids.ids
            tax_datas[line.id] = tax_lines
        return tax_datas

    @api.model
    def _get_gst_tag_ids(self):
        return {
                'cgst_tag_id': self.env.ref('l10n_in.cgst_tag_tax').id,
                'sgst_tag_id': self.env.ref('l10n_in.sgst_tag_tax').id,
                'igst_tag_tax': self.env.ref('l10n_in.igst_tag_tax').id,
                'cess_tag_id': self.env.ref('l10n_in.cess_tag_tax').id,
                }

    @api.multi
    def _invoice_line_group_tax_values(self):
        self.ensure_one()
        tax_datas = {}
        gst_tag = self._get_gst_tag_ids()
        TAX = self.env['account.tax']
        company_id = self.env.user.company_id
        for line_id ,line_taxs in self._invoice_line_tax_values().items():
            rate = 0
            cess_amount = 0
            base_amount = 0
            for line_tax in line_taxs:
                base_amount = line_tax.get('base') or 0
                tax_rate = TAX.browse(line_tax['id']).amount
                if gst_tag['cgst_tag_id'] in line_tax.get('tag_ids') or []:
                    rate += tax_rate
                if gst_tag['sgst_tag_id'] in line_tax.get('tag_ids') or []:
                    rate += tax_rate
                if gst_tag['igst_tag_tax'] in line_tax.get('tag_ids') or []:
                    rate = tax_rate
                if gst_tag['cess_tag_id'] in line_tax.get('tag_ids') or []:
                    cess_amount += line_tax['amount']
            base_amount = self.currency_id.with_context(date=self.date_invoice).compute(base_amount,company_id.currency_id)
            tax_datas.setdefault(rate,{}).update({'base_amount':[base_amount] + (tax_datas[rate].get('base_amount') or []), 'cess_amount': [cess_amount] + (tax_datas[rate].get('cess_amount') or [])})
        return tax_datas
