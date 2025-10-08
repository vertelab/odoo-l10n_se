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

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re

import logging

_logger = logging.getLogger(__name__)


# ["code","in",[3001,3002]]
class FinancialReportsLine(models.Model):
    _name = "financial.reports.line"
    _description = "financial reports line"

    name = fields.Char(string="name", required=True)
    parent_id = fields.Many2one(comodel_name='financial.reports')
    invert_value = fields.Boolean()
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
    account_char_list = fields.Char(string="Accounts", help="a comma seperated list of accounts to find invoice lines for")
    taxes_char_list = fields.Char(string='Taxes',help="a comma seperated list of taxes to find invoice lines for")
    originator_tax_char_list = fields.Char(string="Originator Taxes", help="a comma seperated list of originator taxes to find invoice lines for")
    domain_expression = fields.Char(string="Domain", help="set a regular odoo domain if you can't use the other lines")
    
    def _return_move_lines(self, date_from, date_stop, state):
        self.ensure_one()
        accounts = []
        taxes = []
        domain = []
        originator_taxes = []
        if self.domain_expression:
            try:
                extra_domain = safe_eval(self.domain_expression)
                if isinstance(extra_domain, list):
                    domain += extra_domain
                else:
                    raise UserError(_("Domain expression must be a list."))
            except Exception as e:
                raise UserError(_("Invalid domain expression: %s") % e)
        
        if self.account_char_list:
           accounts = self.account_char_list.split(',')
           domain.append(('account_id.code','in',accounts))
           
        if self.taxes_char_list:
           taxes = self.taxes_char_list.split(',')
           domain.append(('tax_ids.name','in',originator_taxes))
           
        if self.originator_tax_char_list:
           originator_taxes = self.originator_tax_char_list.split(',')
           domain.append(('tax_line_id.name','in',originator_taxes))
           
        domain.append(('date','>=',date_from))
        domain.append(('date','<=',date_stop))
        
        move_lines = self.env['account.move.line'].search(domain)
           
        total = sum(move_lines.mapped(self.amount_type))
        if self.invert_value:
            total = -total
        return total, move_lines  # Optionally return the lines too
        #use amount_type to sum
        # Use accounts,taxes,domain,date_from,date_to and state to find lines
        

    # ~ @api.model
    # ~ def create(self, vals):
        # ~ res = super(FinancialReportsLine, self).create(vals)
        # ~ for record in res:

            # ~ if record.domain_account_move_line:
                # ~ accounts = record.domain_account_move_line.split(',')
                # ~ for account in accounts:
                    # ~ account_domain = "[('account_id','=','" + account + "')]"
                    # ~ _logger.error(f"{account_domain=}")
                # ~ try:
                    # ~ account_result = self.env['account.move.line'].search(eval(account_domain))
                    # ~ _logger.error(f"{account_result=}")
                # ~ except Exception as e:
                    # ~ raise UserError(f"{record.domain_account_move_line} is not a valid domain")

            # ~ if record.domain_expressions_line:

                # ~ taxes = record.domain_expressions_line.split(' ')
                # ~ for tax in taxes:
                    # ~ regex_bal = re.search('bal\[(\d*,*)*]')
                    # ~ _logger.error(f"{regex_bal=}")
                    # ~ regex_crd = re.search('crd\[(\d*,*)*]')
                    # ~ _logger.error(f"{regex_crd=}")
                    # ~ regex_deb = re.search('deb\[(\d*,*)*]')
                    # ~ _logger.error(f"{regex_deb=}")

            # ~ if record.domain_code_move_line:
                # ~ try:
                    # ~ code_result = self.env['account.move.line'].search(eval(record.domain_code_move_line))
                    # ~ _logger.error(f"{code_result=}")
                # ~ except Exception as e:
                    # ~ raise UserError(f"{record.domain_code_move_line} is not a valid domain")
        # ~ return res

    # ~ def write(self, vals):
        # ~ res = super(FinancialReportsLine, self).write(vals)
        # ~ if self.domain_account_move_line:
            # ~ accounts = self.domain_account_move_line.split(',')
            # ~ for account in accounts:
                # ~ account_domain = "[('account_id','=','" + account + "')]"
                #_logger.error(f"{account_domain=}")
            # ~ try:
                # ~ account_result = self.env['account.move.line'].search(eval(account_domain))
                # ~ _logger.error(f"{account_result=}")
            # ~ except Exception as e:
                # ~ raise UserError(f"{self.domain_account_move_line} is not a valid domain")

        # ~ if self.domain_expressions_line:
            # ~ taxes = self.domain_expressions_line.split(',')
            # ~ for tax in taxes:
                # ~ tax_domain = "[('account_id','=','" + tax + "')]"

            # ~ try:
                # ~ tax_result = self.env['account.move.line'].search(eval(tax_domain))
                # ~ _logger.error(f"{tax_result=}")
            # ~ except Exception as e:
                # ~ raise UserError(f"{self.domain_expressions_line} is not a valid domain")

        # ~ if self.domain_code_move_line:
            # ~ try:
                # ~ code_result = self.env['account.move.line'].search(eval(self.domain_code_move_line))
                # ~ _logger.error(f"{code_result=}")
            # ~ except Exception as e:
                # ~ raise UserError(f"{self.domain_code_move_line} is not a valid domain")
