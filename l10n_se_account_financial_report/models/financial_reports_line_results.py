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
    _description = "Financial Reports Line Results"
    _order = "sequence, id"
    
    name = fields.Char(related="report_line_id.description")
    result = fields.Char()
    report_line_id = fields.Many2one('financial.reports.line', string='Report Line')
    report_instance_id = fields.Many2one('financial.reports.instance', string='Report Instance')
    move_line_ids = fields.Many2many('account.move.line', string='Move Lines')
    sequence = fields.Integer(related="report_line_id.sequence")
    domain = fields.Char()
    def get_line_action(self):
        # Example: open related account.move.line records in a tree view
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Move Lines'),
            'view_mode': 'list,form',
            'res_model': 'account.move.line',
            'domain': [('id', 'in', self.move_line_ids.ids)],
            'context': dict(self.env.context),
        }


    
