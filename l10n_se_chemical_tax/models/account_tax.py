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
        
        
        # ~ if self.amount_type == 'fixed':            
            # ~ if base_amount:
                # ~ return math.copysign(quantity, base_amount) * self.amount
            # ~ else:
                # ~ return quantity * self.amount

        # ~ price_include = self._context.get('force_price_include', self.price_include)

        # ~ # base * (1 + tax_amount) = new_base
        # ~ if self.amount_type == 'percent' and not price_include:
            # ~ return base_amount * self.amount / 100
        # ~ # <=> new_base = base / (1 + tax_amount)
        # ~ if self.amount_type == 'percent' and price_include:
            # ~ return base_amount - (base_amount / (1 + self.amount / 100))
        # ~ # base / (1 - tax_amount) = new_base
        # ~ if self.amount_type == 'division' and not price_include:
            # ~ return base_amount / (1 - self.amount / 100) - base_amount if (1 - self.amount / 100) else 0.0
        # ~ # <=> new_base * (1 - tax_amount) = base
        # ~ if self.amount_type == 'division' and price_include:
            # ~ return base_amount - (base_amount * (self.amount / 100))
        # ~ # default value for custom amount_type
        # ~ return 0.0
    
   

