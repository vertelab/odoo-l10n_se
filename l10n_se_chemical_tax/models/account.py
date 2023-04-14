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

           
    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        amount = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner)
        if not product:
            return amount
        price_include = self._context.get('force_price_include', self.price_include)
        if self.amount_type == 'chemical_tax' and not price_include:
            return quantity * product.chemical_tax
        if self.amount_type == 'chemical_tax' and price_include:
            return (self.amount * quantity) + (quantity * product.chemical_tax)
            ## ~ return base_amount + (quantity * product.chemical_tax)          
        return amount


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"
    amount_type = fields.Selection(selection_add=[('chemical_tax', 'Chemical Tax')],
                                   ondelete={'chemical_tax': 'set default'})


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    hidden_tax = fields.Float(string="Hidden tax", readonly=True)
    subtotal_plus_hidden_tax = fields.Float(string="subtotal_plus_hidden_tax", readonly=False, digits=(0,0))
    price_unit_plus_hidden_tax = fields.Float(string="subtotal_plus_hidden_tax", readonly=False, digits=(0,0))
    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category")
    
    @api.model
    def x_get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        res = super(AccountMoveLine, self)._get_price_total_and_subtotal_model(price_unit, quantity, discount, currency, product, partner, taxes, move_type)
        for tax in taxes:
            if product and product.hs_code_id:
                # ~ if tax.hidden_tax and tax.price_include:
                        # ~ chemical_tax = tax._compute_amount(res['price_subtotal'], price_unit, quantity, product, partner)
                        _logger.warning(f"{res['price_subtotal']=}")
                        # ~ res['price_subtotal'] -= chemical_tax
                        
                        # ~ res['price_total'] = res['price_total'] + chemical_tax
                # ~ if tax.hidden_tax and not tax.price_include:
                        # ~ chemical_tax = tax._compute_amount(res['price_subtotal'], price_unit, quantity, product, partner)
                        # ~ res['price_subtotal'] = res['price_subtotal'] + chemical_tax
                    
        return res

class AccountMove(models.Model):
    _inherit = "account.move"

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, tracking=True,
                                     compute='_compute_amount')

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", readonly=True)

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id','line_ids.tax_ids','line_ids.tax_ids.hidden_tax')
    def _compute_invoice_taxes_by_group(self):
        res = super(AccountMove, self)._compute_invoice_taxes_by_group()
        for move in self:
            new_amount_by_group = []
            for line in move.amount_by_group:
                tax_group = self.env['account.tax.group'].search([('name','=',line[0])])
                if not tax_group.hidden_tax:
                   new_amount_by_group.append(line)
            move.amount_by_group = new_amount_by_group
    
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
            # ~ ## Remove hidden tax from amount tax and add it to amount_untaxed
            for line in move.line_ids:
                line.hidden_tax = 0
                line.subtotal_plus_hidden_tax = line.price_subtotal
                line.price_unit_plus_hidden_tax = line.price_unit
                for tax in line.tax_ids:
                    if tax.hidden_tax:
                        hidden_tax = line.tax_ids.filtered(lambda x: x.hidden_tax)._compute_amount(line.price_subtotal,line.price_unit,line.quantity,line.product_id,move.partner_id)
                       
                        move.amount_untaxed = move.amount_untaxed + hidden_tax
                        line.hidden_tax += hidden_tax
                        if not tax.price_include:
                            line.subtotal_plus_hidden_tax = line.price_subtotal + hidden_tax
                            line.price_unit_plus_hidden_tax = line.price_unit + (hidden_tax/line.quantity)
        return res

class AccountFiscalPosition(models.Model):
    _name = "account.fiscal.position"
    _inherit = ["account.fiscal.position"]
    
    # ~ tax_balance_ids = fields.One2many('account.fiscal.position.tax.balance', 'position_id',
                                      # ~ string='Tax Balance Mapping', copy=True)
                                      
    hidden_tax = fields.Boolean(string="Hide Chemical Tax", default=False)
    
