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
    
    # ~ line_id = fields.Many2one("financial.reports.line")
    account_ids = fields.Many2one("account.move.line")
    # ~ få ut alla konton ur domänerna genom for loop
    # ~ samma som samlingen av domäner
    jurnal_id = fields.Many2one(related="account_ids.account_id")
    name = fields.Char()
    # ~ line_name = fields.Char(related="line_id.name", store=True, readonly=False)
    # ~ credit sammlat av alla konton
    credit = fields.Char()
    # ~ debit sammlat av alla konton
    debit = fields.Char()
    
    domain_id = fields.One2many("financial.reports.line","domain_account_move_line")
    
    # ~ @api.model
    # ~ def create(self, values):
        # ~ """Override default Odoo create function and extend."""
        # ~ # Do your custom logic here
        # ~ record = self.env['inancial.reports.line.results'].create({'name': 'Example'})
        # ~ return super(ResPartner, self).create(record)
    
    
    # ~ def create_button(self):
        # ~ _logger.error(f"{self.line_name=}")
            
    
    
    
    
