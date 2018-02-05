# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrExpenseRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    check_amount_in_words = fields.Char(string="Amount in Words")
    payment_method_code_2 = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      string="Payment Method Code 2",
                                      readonly=True)

    @api.onchange('amount')
    def _onchange_amount(self):
        if hasattr(super(HrExpenseRegisterPaymentWizard, self), '_onchange_amount'):
            super(HrExpenseRegisterPaymentWizard, self)._onchange_amount()
        self.check_amount_in_words = self.currency_id.amount_to_text(self.amount)

    def _get_payment_vals(self):
        res = super(HrExpenseRegisterPaymentWizard, self)._get_payment_vals()
        if self.payment_method_id == self.env.ref('account_check_printing.account_payment_method_check'):
            res.update({
                'check_amount_in_words': self.check_amount_in_words,
            })
        return res
