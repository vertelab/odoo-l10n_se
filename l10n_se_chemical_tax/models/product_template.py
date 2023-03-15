# -*- coding: utf-8 -*-

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"
    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", compute="_compute_chem_tax_template", inverse="_set_chem_tax_template",
    search='_search_chem_tax_template', readonly=True)

    @api.depends('product_variant_ids', 'product_variant_ids.chemical_tax')
    def _compute_chem_tax_template(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.chemical_tax = template.product_variant_ids.chemical_tax
        for template in (self - unique_variants):
            template.chemical_tax = 0.0

    def _search_chem_tax_template(self, operator, value):
        products = self.env['product.product'].search([('chemical_tax', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]
    
    def _set_chem_tax_template(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.chemical_tax = template.chemical_tax


