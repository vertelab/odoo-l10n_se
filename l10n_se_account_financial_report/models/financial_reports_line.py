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

import logging
_logger = logging.getLogger(__name__)

# ["code","in",[3001,3002]]
class FinancialReportsLine(models.Model):
    _name = "financial.reports.line"
    _description = "financial reports line"

    # Har ett namn.
    name = fields.Char(string="name", required=True)

    parent_id = fields.Many2one(comodel_name='financial.reports')
    # ~ tax_ids = fields.Many2many(comodel_name='account.tax', string='Account Tax')
    domain_account_move_line = fields.Char(string="Account Move Line Domain", store=True)
    domain_tax_line = fields.Char(string="Domain Tax Line", store=True)
    domain_code = fields.Char(string="Domain Code", store=True)
        
    @api.model
    def create(self, vals):
        res = super(FinancialReportsLine, self).create(vals)
        for record in res:
            
            if record.domain_account_move_line:
                accounts = record.domain_account_move_line.split(',')
                for account in accounts:
                    account_domain = "[('account_id','=','"+account+"')]"
                    _logger.error(f"{account_domain=}")
                try:
                    account_result = self.env['account.move.line'].search(eval(account_domain))
                    _logger.error(f"{account_result=}")
                except:
                    raise UserError(f"{record.domain_account_move_line} is not a valid domain")
                    
            if record.domain_tax_line:
                taxes = record.domain_tax_line.split(',')
                for tax in taxes:
                    tax_domain = "[('account_id','=','"+tax+"')]"
                    _logger.error(f"{tax_domain=}")
                try:
                    tax_result = self.env['account.move.line'].search(eval(tax_domain))
                    _logger.error(f"{tax_result=}")
                except:
                    raise UserError(f"{record.domain_tax_line} is not a valid domain")
                    
            if record.domain_code:
                try:
                    code_result = self.env['account.move.line'].search(eval(record.domain_code))
                    _logger.error(f"{code_result=}")
                except:
                    raise UserError(f"{record.domain_code} is not a valid domain")
        return res
        
    def write(self, vals):
        res = super(FinancialReportsLine, self).write(vals)
        # ~ for record in res:
            
        if self.domain_account_move_line:
            accounts = self.domain_account_move_line.split(',')
            for account in accounts:
                account_domain = "[('account_id','=','"+account+"')]"
                # ~ _logger.error(f"{account_domain=}")
            try:
                account_result = self.env['account.move.line'].search(eval(account_domain))
                _logger.error(f"{account_result=}")
            except:
                raise UserError(f"{self.domain_account_move_line} is not a valid domain")
                
        if self.domain_tax_line:
            taxes = self.domain_tax_line.split(',')
            for tax in taxes:
                tax_domain = "[('account_id','=','"+tax+"')]"
                # ~ _logger.error(f"{tax_domain=}")
                
            try:
                tax_result = self.env['account.move.line'].search(eval(tax_domain))
                _logger.error(f"{tax_result=}")
                # ~ for dom in tax_result:
                    # ~ _logger.error("hej")
            except:
                raise UserError(f"{self.domain_tax_line} is not a valid domain")
        
        if self.domain_code:
            try:
                code_result = self.env['account.move.line'].search(eval(self.domain_code))
                _logger.error(f"{code_result=}")
            except:
                    raise UserError(f"{self.domain_code} is not a valid domain")
        # ~ return res




