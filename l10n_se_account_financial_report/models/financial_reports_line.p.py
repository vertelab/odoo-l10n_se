# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

import logging

_logger = logging.getLogger(__name__)


class FinancialReportsLine(models.Model):
    _name = "financial.reports.line"
    _description = "financial reports line"
    _order = "sequence, id"
    name = fields.Char(string="name", required=True)
    description = fields.Char()
    parent_id = fields.Many2one(comodel_name='financial.reports')
    invert_value = fields.Boolean()
    sequence = fields.Integer(default=1)
    amount_type = fields.Selection(
        [
            ('balance', 'Balance'),
            ('credit', 'Credit'),
            ('debit', 'Debit'),
        ],
        string='Amount Type',
        default='balance', 
        required=True  
    )
    account_char_list = fields.Char(
        string="Accounts", help="a comma separated list of accounts to find invoice lines for")
    taxes_char_list = fields.Char(string='Taxes',help="a comma separated list of taxes to find invoice lines for")
    originator_tax_char_list = fields.Char(
        string="Originator Taxes", help="a comma separated list of originator taxes to find invoice lines for")
    domain_expression = fields.Char(string="Domain", help="set a regular odoo domain if you can't use the other lines")
        
