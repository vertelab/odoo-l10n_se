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

import logging
_logger = logging.getLogger(__name__)

# ["code","in",[3001,3002]]
class FinancialReportsLine(models.Model):
    _name = "financial.reports.line"
    _description = "financial reports line"

    # Har ett namn.
    name = fields.Char(string="name")

    # Har ett text fält med konton.
    # account_domain = fields.Char()

    parent_id = fields.Many2one(comodel_name='financial.reports')
    # instance = fields.Many2one(comodel_name="financial.reports.instance")
    instance = fields.One2many(comodel_name="financial.reports.instance", inverse_name="line_ids")

    # company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    # tax_ids = fields.Many2many(comodel_name='account.tax', string='Account Tax')

    # account_ids = fields.Many2many(
    #     comodel_name="account.account", string="Accounts")
    
    domain_account_move_line = fields.Char(string="Account Move Line Domain")


    #funktion för att vlidera domän; bara fångar ett fel; search
    #en funktion för att validera domäner, använd en search, behöver bara fånga ett fel just nu
    # self.env['account.financial.report'].search([('name', '=', u'BALANSRÄKNING'), ('parent_id', '=', self.report_id.id)])

    # def search_domain(self):
    #     if self.env['account.financial.report'].search([('name', '=', something)]):
    #         _logger.error("search")


