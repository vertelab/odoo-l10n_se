# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class HSCode(models.Model):
    _inherit = "hs.code"

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category", store=True)
    chemical_max_tax = fields.Float(string="Chemical max tax", help="Chemical max tax for products in this category")
    tax_article_number = fields.Selection(
        [('1', 'Punkt 1'), ('2', 'Punkt 2'), ('3', 'Punkt 3'), ('4', 'Punkt 4'), ('5', 'Punkt 5'), ('6', 'Punkt 6'),
         ('6', 'Punkt 6'), ('7', 'Punkt 7'), ('8', 'Punkt 8'), ('9', 'Punkt 9'), ('10', 'Punkt 10'), ('11', 'Punkt 11'),
         ('12', 'Punkt 12'), ('13', 'Punkt 13')], 'Kategori enl. Skatteverkets tabell', default='8')
