# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.tools.float_utils import float_is_zero


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"
    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line')

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('sale_line_id')
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
        keys_sorted.append(move.sale_line_id.id)
        return keys_sorted

    def _action_done(self):
        result = super(StockMove, self)._action_done()
        for line in self.mapped('sale_line_id'):
            line.qty_delivered = line._get_delivered_qty()
        return result

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'product_uom_qty' in vals:
            for move in self:
                if move.state == 'done':
                    sale_order_lines = self.filtered(lambda move: move.sale_line_id).mapped('sale_line_id')
                    for line in sale_order_lines:
                        line.qty_delivered = line._get_delivered_qty()
        return res

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id): #TODO OCO c'est ici dedans qu'il va falloir bidouiller, je pense !
        #TODO OCO DOC override
        res = super(StockMove, self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)

        if self._is_out() and self.company_id.anglo_saxon_accounting and self._get_related_invoices():

            product_accounts = self.product_id.product_tmpl_id._get_product_accounts()
            interim_output_account = product_accounts['stock_output']
            interim_output_invoice_move_lines = self.env['account.move.line'].search([('move_id', 'in', self._get_related_invoices().mapped('move_id.id')), ('account_id', '=', interim_output_account.id)])

            # TODO OCO recherche de la valeur de débit de ce stock move
            debit_val = None
            for res_line in res:
                line_data = res_line[2]
                if line_data['account_id'] == interim_output_account.id:
                    debit_val = line_data['debit']
                    break

            if debit_val == None:
                raise UserError(_("No debit valuation in interim account"))

            #TODO OCO Calcul du montant rectificatif à écrire
            previous_stock_moves = self.env['stock.move'].search([('state', '=', 'done'), ('group_id', '=' , self.group_id.id), ('id', '!=', self.id)])
            previously_shipped_qty = sum(previous_stock_moves.mapped('product_qty'))
            sorted_invoice_move_lines = interim_output_invoice_move_lines.sorted(key=lambda x: x.date)
            invoice_valuation = 0.0
            qty_to_treat = self.product_qty
            import pdb; pdb.set_trace()
            for invoice_aml in sorted_invoice_move_lines:

                invoice_aml_qty_left = invoice_aml.quantity

                if not float_is_zero(previously_shipped_qty, precision_rounding=self.product_id.uom_id.rounding):
                    qty_to_substract = min(invoice_aml.quantity, previously_shipped_qty)
                    previously_shipped_qty -= qty_to_substract
                    invoice_aml_qty_left = invoice_aml.quantity - qty_to_substract

                if invoice_aml_qty_left:
                    treated_qty = min(qty_to_treat, invoice_aml_qty_left)
                    invoice_valuation += (invoice_aml.balance / invoice_aml.quantity) * treated_qty
                    qty_to_treat -= treated_qty

                if float_is_zero(qty_to_treat, precision_rounding=self.product_id.uom_id.rounding):
                    break

            # TODO OCO génération des données d'aml supplémentaires

            difference_with_invoice = debit_val + invoice_valuation

            if not self.company_id.currency_id.is_zero(difference_with_invoice):
                balancing_output_line_vals = {
                    'name': _('Effective inventory valuation correction'),
                    'product_id': self.product_id.id,
                    'quantity': qty,
                    'product_uom_id': self.product_id.uom_id.id,
                    'ref': self.picking_id.name,
                    'partner_id': self.partner_id.id,
                    'credit': difference_with_invoice > 0 and difference_with_invoice or 0,
                    'debit': difference_with_invoice < 0 and -difference_with_invoice or 0,
                    'account_id': interim_output_account.id,
                }

                balancing_output_counterpart_line_vals = {
                    'name': _('Effective inventory valuation correction'),
                    'product_id': self.product_id.id,
                    'quantity': qty,
                    'product_uom_id': self.product_id.uom_id.id,
                    'ref': self.picking_id.name,
                    'partner_id': self.partner_id.id,
                    'credit': difference_with_invoice < 0 and -difference_with_invoice or 0,
                    'debit': difference_with_invoice > 0 and difference_with_invoice or 0,
                    'account_id': product_accounts['expense'].id,
                }

                res.append((0, 0, balancing_output_line_vals))
                res.append((0, 0, balancing_output_counterpart_line_vals))

        return res

    def _get_related_invoices(self):
        """ Overridden from stock_account to return the customer invoices
        related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        rslt += self.picking_id.sale_id.invoice_ids.filtered(lambda x: x.state not in ('draft', 'cancel'))
        return rslt


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', 'Sale Order')


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(ProcurementRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        if values.get('sale_line_id', False):
            result['sale_line_id'] = values['sale_line_id']
        if values.get('partner_dest_id'):
            result['partner_id'] = values['partner_dest_id'].id
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one(related="group_id.sale_id", string="Sales Order", store=True)

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPicking, self)._create_backorder(backorder_moves)
        for picking in self.filtered(lambda pick: pick.picking_type_id.code == 'outgoing'):
            backorder = picking.search([('backorder_id', '=', picking.id)])
            if backorder.sale_id:
                backorder.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': backorder, 'origin': backorder.sale_id},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return res
