# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)



class ProductCategory(models.Model):
    _inherit = "product.category"
    
    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", store=True)
    chemical_max_tax = fields.Float(string="Chemical max tax", help="Chemical max tax for products in this category")
    elkretsen_miljoavgift = fields.Float(string="elkretsen_miljoavgift", help="environmental fee for products in this category")



class ProductProduct(models.Model):
    _inherit = "product.product"
    
    
    @api.depends("net_weight","categ_id.chemical_tax", "categ_id.chemical_max_tax")
    def _chemical_compute(self):
        for product in self:
            product.chemical_max_tax = product.categ_id.chemical_max_tax
            product.chemical_tax = product.categ_id.chemical_tax * product.net_weight
            if product.chemical_tax > product.chemical_max_tax:
                product.chemical_tax = product.chemical_max_tax
     
    chemical_tax = fields.Float(string="Chemical tax", help="Computed chemical tax", compute="_chemical_compute", store=True) 
    
    chemical_max_tax = fields.Float(string="Chemical max tax", help="Chemical max tax for products in this category")
    elkretsen_miljoavgift = fields.Float(string="elkretsen_miljoavgift", help="environmental fee for products in this category")

