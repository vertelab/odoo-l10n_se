# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"
    hidden_tax = fields.Boolean(string="hide Chemical Tax", default=False)


class AccountTax(models.Model):
    _inherit = "account.tax"

    hidden_tax = fields.Boolean(related="tax_group_id.hidden_tax")

    amount_type = fields.Selection(selection_add=[('chemical_tax', 'Chemical Tax')],
                                   ondelete={'chemical_tax': 'set default'})

    # ~ tax_group_id = fields.Selection(selection_add = [('chemical_tax', 'ChemTax')], ondelete = {'chemical_tax':
    # 'set default'})

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
    amount_type = fields.Selection(selection_add=[('chemical_tax', 'Chemical Tax')],
                                   ondelete={'chemical_tax': 'set default'})


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category")

    # @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'chemical_tax')
    # def _onchange_price_subtotal(self):
    #     for line in self:
    #         if not line.move_id.is_invoice(include_receipts=True):
    #             continue

    #         line.update(line._get_price_total_and_subtotal())
    #         line.update(line._get_fields_onchange_subtotal())

    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     for line in self:
    #         if not line.product_id or line.display_type in ('line_section', 'line_note'):
    #             continue

    #         line.name = line._get_computed_name()
    #         line.account_id = line._get_computed_account()
    #         taxes = line._get_computed_taxes()
    #         if taxes and line.move_id.fiscal_position_id:
    #             taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
    #         line.tax_ids = taxes
    #         line.product_uom_id = line._get_computed_uom()
    #         line.price_unit = line._get_computed_price_unit()
    #         line.chemical_tax = line.product_id.chemical_tax

    # @api.model
    # def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
    #                                         move_type):
    #     ''' This method is used to compute 'price_total' & 'price_subtotal'.

    #     :param price_unit:  The current price unit.
    #     :param quantity:    The current quantity.
    #     :param discount:    The current discount.
    #     :param currency:    The line's currency.
    #     :param product:     The line's product.
    #     :param partner:     The line's partner.
    #     :param taxes:       The applied taxes.
    #     :param move_type:   The type of the move.
    #     :return:            A dictionary containing 'price_subtotal' & 'price_total'.
    #     '''
    #     res = {}

    #     # Compute 'price_subtotal'.
    #     line_discount_price_unit = price_unit * (1 - (discount / 100.0))
    #     subtotal = quantity * line_discount_price_unit

    #     # Compute 'price_total'.
    #     if taxes:
    #         taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
    #                                                                          quantity=quantity, currency=currency,
    #                                                                          product=product, partner=partner,
    #                                                                          is_refund=move_type in (
    #                                                                          'out_refund', 'in_refund'))
    #         res['price_subtotal'] = taxes_res['total_excluded']
    #         res['price_subtotal'] = res['price_subtotal'] + (self.quantity * self.chemical_tax)

    #         res['price_total'] = taxes_res['total_included']
    #         res['price_total'] = res['price_total'] + (self.quantity * self.chemical_tax)
    #     else:
    #         res['price_total'] = res['price_subtotal'] = subtotal + (self.quantity * self.chemical_tax)
    #     # In case of multi currency, round before it's use for computing debit credit
    #     if currency:
    #         res = {k: currency.round(v) for k, v in res.items()}
    #     return res


class AccountMove(models.Model):
    _inherit = "account.move"

    #hidden_tax = fields.Boolean(string="Hide Chemical Tax")

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, tracking=True,
                                     compute='_compute_amount')

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", readonly=True)


    # @api.depends('price_unit', 'categ_id.chemical_tax')

    # @api.depends("account_tax_id.amount_untaxed", "account_tax_id.hidden_tax")

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
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.tax_ids',
        'line_ids.tax_ids.hidden_tax',
        )
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            ## Remove hidden tax from amount tax and add it to amount_untaxed
            for line in move.line_ids:
                if line.tax_ids.filtered(lambda x: x.hidden_tax):
                    hidden_tax = line.tax_ids.filtered(lambda x: x.hidden_tax)._compute_amount(line.price_subtotal,line.price_unit,line.quantity,line.product_id,move.partner_id)
                    move.amount_untaxed = move.amount_untaxed + hidden_tax
                    move.amount_tax = move.amount_tax - hidden_tax
        return res
    

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id','line_ids.tax_ids','line_ids.tax_ids.hidden_tax')
    def _compute_invoice_taxes_by_group(self):
        res = super(AccountMove, self)._compute_invoice_taxes_by_group()
        for move in self:
            new_amount_by_group = []
            for line in move.amount_by_group:
                _logger.warning(f"{line[0]=}")
                tax_group = self.env['account.tax.group'].search([('name','=',line[0])])
                _logger.warning(f"{tax_group} {tax_group.name} {tax_group.hidden_tax}")
                if not tax_group.hidden_tax:
                   new_amount_by_group.append(line)
            move.amount_by_group = new_amount_by_group


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    hidden_tax = fields.Boolean(string="Hide Chemical Tax", default=False)
    # amount_untaxed = fields.Monetary(string='Untaxed Amount', readonly=True)
