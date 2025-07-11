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

_logger = logging.getLogger(__name__)


class FinancialReportsInstance(models.Model):
    _name = "financial.reports.instance"
    _description = "financial reports instance"

    name = fields.Char(string="name")
    
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default='draft',
    )

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    
    report_id = fields.Many2one("financial.reports", string="Report")
    result_ids = fields.One2many('financial.reports.line.results', 'report_instance_id')

    def create_button(self):
        for line in self.report_id.lines:
            result, move_lines = line._return_move_lines(self.start_date, self.end_date, self.state)
            self.env['financial.reports.line.results'].create([{
            'result':result,
            'report_line_id':line.id,
            'report_instance_id':self.id,
            'move_line_ids':move_lines.ids,
            }])
