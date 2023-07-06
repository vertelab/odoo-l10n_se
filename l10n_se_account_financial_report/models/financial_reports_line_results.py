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


class FinancialReportsLineResults(models.Model):
    _name = "financial.reports.line.results"
    _description = "financial reports line results"
    
    name = fields.Char()
    # ~ credit sammlat av alla konton
    credit = fields.Char()
    # ~ debit sammlat av alla konton
    debit = fields.Char()
    
    domain_id = fields.One2many("financial.reports.line","domain_account_move_line")
    instance_id = fields.Many2many(comodel_name='financial.reports.instance')
    
    copy_domain_code = fields.Char()
    copy_domain_account = fields.Char()
    copy_domain_tax =fields.Char()
    
    def show_accounts(self):
        for rec in self:
            aco = []
            if rec.copy_domain_account:
                accounts = self.copy_domain_account.split(',')
                for account in accounts:
                    account_domain = "[('account_id','=','"+account+"')]"
                    _logger.error(f"{account_domain=}")
                    account_result = self.env['account.move.line'].search(eval(account_domain))
                    _logger.error(f"{account_result.ids=}")
                    # ~ sheck if två lika dana konton
                    aco.extend(account_result.ids)
                    
            if rec.copy_domain_tax:
                taxes = self.copy_domain_tax.split(',')
                for tax in taxes:
                    tax_domain = "[('account_id','=','"+tax+"')]"
                    _logger.error(f"{tax_domain=}")
                    tax_result = self.env['account.move.line'].search(eval(tax_domain))
                    _logger.error(f"{tax_result.ids=}")
                    # ~ sheck if två lika dana konton
                    aco.extend(tax_result.ids)
            
            if rec.copy_domain_code:
                code_result = self.env['account.move.line'].search(eval(rec.copy_domain_code))
                _logger.error(f"{code_result.ids=}")
                # ~ sheck if två lika dana konton
                aco.extend(code_result.ids)
                
            action = {
            "type": "ir.actions.act_window",
            "name": "Show Accounts",
            "res_model": "account.move.line",
            "view_mode": "tree",
            "target": "current",
            "domain": [("id","in", aco)],
            # ~ "context": ctx,
            }
                
            return action

    
    
    
