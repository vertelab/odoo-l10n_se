# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    hidden_tax = fields.Boolean(string="hide Chemical Tax", default=False)
    
    amount_type = fields.Selection(selection_add = [('chemical_tax', 'Chemical Tax')], ondelete = {'chemical_tax': 'set default'})
    # ~ tax_group_id = fields.Selection(selection_add = [('chemical_tax', 'ChemTax')], ondelete = {'chemical_tax': 'set default'})
    
    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        amount = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner)
        price_include = self._context.get('force_price_include', self.price_include)
        if self.amount_type == 'chemical_tax' and not price_include:
            return quantity * product.chemical_tax
        if self.amount_type == 'chemical_tax' and price_include:
            return (self.amount * quantity) + (quantity * product.chemical_tax)  
            # ~ return base_amount + (quantity * product.chemical_tax)          
        return amount        
        
       
    
class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"
    amount_type = fields.Selection(selection_add = [('chemical_tax', 'Chemical Tax')], ondelete = {'chemical_tax': 'set default'})

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category")
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()
            line.chemical_tax = line.product_id.chemical_tax

    # @api.onchange('chemical_tax')
    # def onchange_chemical_tax(self):
    #     self.price_total = self.price_total + self.chemical_tax

    
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        res['price_total'] = res['price_subtotal'] + (self.quantity * self.chemical_tax)
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'chemical_tax')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.chemical_tax',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        for move in self:

            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = move._get_lines_onchange_currency().currency_id

            for line in move.line_ids:
                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance + line.chemical_tax
                        total_untaxed_currency += line.amount_currency + line.chemical_tax
                        total += line.balance + line.chemical_tax
                        total_currency += line.amount_currency + line.chemical_tax
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            # move.amount_untaxed = move.amount_untaxed + sum(rec.chemical_tax for rec in move.invoice_line_ids)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies or move.company_id.currency_id

            # Compute 'payment_state'.
            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

            if move.is_invoice(include_receipts=True) and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                    new_pmt_state = 'partial'

            if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

                # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                    new_pmt_state = 'reversed'

            move.payment_state = new_pmt_state



class AccountMove(models.Model):
    _inherit = "account.move"

    hidden_tax = fields.Boolean(string="Hide Chemical Tax")

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, tracking=True,
        compute='_compute_amount')
    
    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", readonly=True)
    








    
    #@api.depends('price_unit', 'categ_id.chemical_tax')    

    #@api.depends("account_tax_id.amount_untaxed", "account_tax_id.hidden_tax")
    
    """ def _compute_amount(self, amount_by_group, amount_untaxed, partner=None):
        
        #amount = super(AccountMove, self)._compute_amount(amount_by_group, amount_untaxed, partner)
        
        #self.amount_untaxed = self.amount_untaxed + self.amount_by_group
        price_include = self._context.get('force_price_include', self.price_include)
        if self.hidden_tax == False and not price_include:
           return amount_untaxed * product.chemical_tax         
        if self.hidden_tax == True:
            return (self.amount * quantity) + (quantity * product.chemical_tax) 
        else:
            return  (self.amount * quantity)                 
        #return amount   """

class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    hidden_tax = fields.Boolean(string="Hide Chemical Tax", default=False)
    #amount_untaxed = fields.Monetary(string='Untaxed Amount', readonly=True)
