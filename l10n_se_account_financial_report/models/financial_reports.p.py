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
from odoo.tools.safe_eval import safe_eval

import logging

_logger = logging.getLogger(__name__)


class FinancialReports(models.Model):
    _name = "financial.reports"
    _description = "financial reports"

    name = fields.Char(string="name")

    lines = fields.One2many("financial.reports.line", "parent_id")

    parent_state = fields.Selection([
        ('all', 'All'), ('draft', 'Draft'), ('posted', 'Posted'), ('cancelled', 'Cancelled')
    ])
    date_picker = fields.Many2one(
        'ir.model.fields', string="Date Picker",
        domain=[('ttype', '=', 'date'), ('model_id', '=', 'account.move.line')]
    )

    def action_view_report(self):
        total, move_lines = self._return_move_lines()
        lines = []
        _logger.info(lines)

    def _return_move_lines(self, start_date, end_date, state = False, date_field = False, company_id = False):
        report_domain = []
        if not company_id:
           company_id = self.env.company 
        vals = []
        if not state:
            state = self.parent_state

        if state and state != 'all':
            report_domain.append(('parent_state', '=', state))

        if not date_field:
            date_field = self.date_picker

        if date_field:
            report_domain.append((date_field['name'], '>=', start_date))
            report_domain.append((date_field['name'], '<=', end_date))
        else:
            report_domain.append(('date', '>=', start_date))
            report_domain.append(('date', '<=', end_date))
        _logger.warning(f"{report_domain=}")
        
    
        for line in self.lines:
            domain = []
            domain += report_domain
            if line.account_char_list:
                accounts = line.account_char_list.split(',')
                domain.append(('account_id.code', 'in', accounts))

            if line.taxes_char_list:
                taxes = line.taxes_char_list.split(',')
                domain.append(('tax_ids.name', 'in', taxes))

            if line.originator_tax_char_list:
                originator_taxes = line.originator_tax_char_list.split(',')
                domain.append(('tax_line_id.name', 'in', originator_taxes))

            if line.domain_expression:
                try:
                    extra_domain = safe_eval(self.domain_expression)
                    if isinstance(extra_domain, list):
                        domain += extra_domain
                    else:
                        raise UserError(_("Domain expression must be a list."))
                except Exception as e:
                    raise UserError(_("Invalid domain expression: %s") % e)
            _logger.warning(f"{domain=}")
            move_lines = self.env['account.move.line'].search(domain)
            _logger.warning(f"{move_lines=}")
            line_total = sum(move_lines.mapped(line.amount_type))
            if line.invert_value:
                line_total = -line_total
            vals.append({"name":line.name,"total":line_total,"move_lines":move_lines,"domain":domain,"report_line_id":line})
        return vals


        # return _return_move_lines for each line in template.
    
    
