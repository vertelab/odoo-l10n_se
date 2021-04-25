# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2018 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from odoo.exceptions import Warning, UserError
import logging
_logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    user_type_ids = fields.Many2many('account.account.type', string='Account type')

    @api.onchange('user_type_ids')
    def check_account_ids(self):
        acc_ids = self.env['account.account'].browse()
        for ut in self.user_type_ids:
            acc_ids | self.env['account.account'].search([('user_type_id','=',ut.id)])
        self.account_ids = acc_ids


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    def _compute_practical_amount(self):
        for line in self:
            result = 0.0
            acc_ids = line.general_budget_id.account_ids | self.env['account.account'].search([('user_type_id','in',line.general_budget_id.user_type_ids.mapped('id'))])
            if not acc_ids:
                raise UserError(_("XXThe Budget '%s' has no accounts!") % (line.general_budget_id.name))
            date_to = self.env.context.get('wizard_date_to', line.date_to)
            date_from = self.env.context.get('wizard_date_from', line.date_from)
            # ~ period_id = self.env.context.get('wizard_period_id',line.period_id)
            period_id = None
            if line.analytic_account_id.id:
                if period_id:
                    self.env.cr.execute("""
                        SELECT SUM(amount)
                        FROM account_analytic_line
                        WHERE account_id=%s
                            AND period_id = %s
                            AND general_account_id=ANY(%s)""",
                    (line.analytic_account_id.id, period_id, acc_ids.mapped('id'),))
                else:
                    self.env.cr.execute("""
                        SELECT SUM(amount)
                        FROM account_analytic_line
                        WHERE account_id=%s
                            AND (date between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))
                            AND general_account_id=ANY(%s)""",
                    (line.analytic_account_id.id, date_from, date_to, acc_ids.mapped('id'),))
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
