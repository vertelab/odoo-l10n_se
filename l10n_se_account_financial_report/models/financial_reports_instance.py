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
from datetime import date

import logging
_logger = logging.getLogger("\33[1;37m\33[45m"+__name__+"\33[1;37m\33[42m")


class FinancialReportsInstance(models.Model):
    _name = "financial.reports.instance"
    _description = "financial reports instance"

    name = fields.Char(string="name")

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    report_id = fields.Many2one(comodel_name="financial.reports", string="Report")
    
    line_id = fields.Many2one(comodel_name="financial.reports.line")
    line_name = fields.Char(related="line_id.domain_code_move_line", store=True, readonly=False)
    result_id = fields.Many2many(comodel_name='financial.reports.line.results')
    
    def create_button(self):
        lines_unlinck = self.env['financial.reports.line.results'].search([]).unlink()
        for rec in self:
            for lines in rec.report_id.lines:
                
                #Domain Code
                domain_code_debit = 0
                domain_code_credit = 0
                if lines.domain_code_move_line:
                    domain_search = self.env['account.move.line'].search(eval(lines.domain_code_move_line))
                    for domain in domain_search:
                        domain_browse = self.env['account.move.line'].browse(domain)
                        if self.start_date <= domain_browse.id.date and domain_browse.id.date <= self.end_date:
                            domain_code_debit += domain_browse.id.debit
                            domain_code_credit += domain_browse.id.credit
                        
                #Domain Account
                domain_account_debit = 0
                domain_account_credit = 0
                if lines.domain_account_move_line:
                    account_split = lines.domain_account_move_line.split(',')
                    for split in account_split:
                        account_domain = "[('account_id','=','"+split+"')]"
                        account_search = self.env['account.move.line'].search(eval(account_domain))
                        for account in account_search:
                            account_browse = self.env['account.move.line'].browse(account)
                            if self.start_date <= account_browse.id.date and account_browse.id.date <= self.end_date:
                                domain_account_debit += account_browse.id.debit
                                domain_account_credit += account_browse.id.credit
                                          
                #Domain Tax
                domain_tax_debit = 0
                domain_tax_credit = 0
                if lines.domain_expressions_line:
                    tax_split = lines.domain_expressions_line.split(',')
                    for split in tax_split:
                        tax_domain = "[('account_id','=','"+split+"')]"
                        tax_search = self.env['account.move.line'].search(eval(tax_domain))
                        for tax in tax_search:
                            tax_browse = self.env['account.move.line'].browse(tax)
                            if self.start_date <= tax_browse.id.date and tax_browse.id.date <= self.end_date:
                                domain_tax_debit += tax_browse.id.debit
                                domain_tax_credit += tax_browse.id.credit
                                
                _logger.error(f"{lines.name=}")
                combined_debit = domain_tax_debit + domain_account_debit + domain_code_debit
                _logger.error(f"{combined_debit=}")
                combined_credit = domain_tax_credit + domain_account_credit + domain_code_credit
                _logger.error(f"{combined_credit=}")
                
                vals = [{
                    'name':lines.name,
                    'debit':combined_debit,
                    'credit':combined_credit,
                    'copy_domain_code':lines.domain_code_move_line,
                    'copy_domain_account':lines.domain_account_move_line,
                    'copy_domain_tax':lines.domain_expressions_line,
                    }]
                tmp = self.env['financial.reports.line.results'].create(vals)
                



