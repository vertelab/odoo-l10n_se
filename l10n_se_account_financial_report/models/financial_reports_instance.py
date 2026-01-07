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
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
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
    target_moves = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
            ('all', 'All'),
        ],
        string='Target Moves',
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default='posted',
    )
    
    report_id = fields.Many2one("financial.reports", string="Report")
    result_ids = fields.One2many('financial.reports.line.results', 'report_instance_id')
    
    def button_draft(self):
        self.state = "draft"
        self.result_ids.unlink()
    
    def view_report(self):
        """Open list view of result_ids"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Report Results',
            'res_model': 'financial.reports.line.results',
            'view_mode': 'list,form',
            'domain': [('report_instance_id', '=', self.id)],
            'context': {'default_report_instance_id': self.id},
            'target': 'current',
        }

    def create_report(self):
        self.state = "done"
        
        result = self.report_id._return_move_lines(self.start_date, self.end_date, self.target_moves, self.report_id.date_picker, self.company_id)
        for line in result:
                        # ~ vals.append({"name":line.name,"total":line_total,"move_lines":move_lines,"domain":domain,"report_line_id":line})
            self.env['financial.reports.line.results'].create([{
                'result':line['total'],
                'report_line_id':line['report_line_id'].id,
                'report_instance_id':self.id,
                'move_line_ids':line['move_lines'],
                'domain':line['domain'],
            }])

