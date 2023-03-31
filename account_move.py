# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _inherit = "product.category"
    
    # chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", readonly=True)
""" 
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    price_with_chemtax = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )

    @api.depends('price_unit', 'categ_id.chemical_tax')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0) """