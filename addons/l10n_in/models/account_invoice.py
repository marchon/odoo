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

    @api.multi
    def _invoice_line_group_tax_values(self, line_id=False):
        self.ensure_one()
        tax_datas = {}
        cgst_tag_id = self.env.ref('l10n_in.cgst_tag_tax').id
        sgst_tag_id = self.env.ref('l10n_in.sgst_tag_tax').id
        igst_tag_tax = self.env.ref('l10n_in.igst_tag_tax').id
        cess_tag_id = self.env.ref('l10n_in.cess_tag_tax').id
        TAX = self.env['account.tax']
        all_tax = {'igst':0, 'cgst':0, 'sgst':0, 'cess':0}
        for line in self.mapped('invoice_line_ids').filtered(lambda i: line_id and line_id == i.id or i.id):
            rate = 0
            cess_amount = 0
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)['taxes']
            for tax_line in tax_lines:
                tax = TAX.browse(tax_line['id'])
                if cgst_tag_id in tax.tag_ids.ids:
                    rate += tax.amount
                    all_tax['cgst'] += tax_line['amount']
                if sgst_tag_id in tax.tag_ids.ids:
                    rate += tax.amount
                    all_tax['sgst'] += tax_line['amount']
                if igst_tag_tax in tax.tag_ids.ids:
                    rate = tax.amount
                    all_tax['igst'] += tax_line['amount']
                if cess_tag_id in tax.tag_ids.ids:
                    cess_amount += tax_line['amount']
                    all_tax['cess'] += tax_line['amount']
            tax_datas.setdefault(rate,{}).update({'base_amount':line.price_subtotal + (tax_datas[rate].get('base_amount') or 0), 'cess_amount': cess_amount + (tax_datas[rate].get('cess_amount') or 0)})
        if line_id:
            return all_tax
        return tax_datas
