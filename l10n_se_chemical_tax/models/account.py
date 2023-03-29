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

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'chemical_tax')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

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

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
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
                                                                             quantity=quantity, currency=currency,
                                                                             product=product, partner=partner,
                                                                             is_refund=move_type in (
                                                                             'out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_subtotal'] = res['price_subtotal'] + (self.quantity * self.chemical_tax)

            res['price_total'] = taxes_res['total_included']
            res['price_total'] = res['price_total'] + (self.quantity * self.chemical_tax)
        else:
            res['price_total'] = res['price_subtotal'] = subtotal + (self.quantity * self.chemical_tax)
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    hidden_tax = fields.Boolean(string="Hide Chemical Tax")

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


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    hidden_tax = fields.Boolean(string="Hide Chemical Tax", default=False)
    # amount_untaxed = fields.Monetary(string='Untaxed Amount', readonly=True)
