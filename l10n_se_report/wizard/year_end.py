# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class year_end_wizard(models.TransientModel):
    _name = 'year.end.wizard'

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year', default=_get_year)
    trial_balance_account = fields.Many2one(comodel_name='account.account', string='Trial Balance Account')
    income_statement_account = fields.Many2one(comodel_name='account.account', string='Income Statement Account')
    trial_balance = fields.Float(string='Trial Balance', default=0.0, readonly=True)
    income_statement = fields.Float(string='Income Statement', default=0.0, readonly=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', help='Entry journal')
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('all', 'All Entries')], string='Target Moves')

    @api.one
    @api.onchange('fiscalyear_id', 'target_move')
    def read_account(self):
        if self.fiscalyear_id:
            start_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('date_start', '=', self.fiscalyear_id.date_start), ('special', '=', True)])
            end_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('date_stop', '=', self.fiscalyear_id.date_stop)])
            self.trial_balance = self.trial_balance_account.with_context({'period_from': start_period.id, 'period_to': end_period.id, 'state': self.target_move}).balance
            self.income_statement = self.income_statement_account.with_context({'period_from': start_period.id, 'period_to': end_period.id, 'state': self.target_move}).balance

    @api.multi
    def create_entry(self):
        if self.fiscalyear_id:
            # data disappeared in this case...
            start_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('date_start', '=', self.fiscalyear_id.date_start), ('special', '=', True)])
            end_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('date_stop', '=', self.fiscalyear_id.date_stop)])
            trial_balance = self.trial_balance_account.with_context({'period_from': start_period.id, 'period_to': end_period.id, 'state': self.target_move}).balance
            income_statement = self.income_statement_account.with_context({'period_from': start_period.id, 'period_to': end_period.id, 'state': self.target_move}).balance
            trba = abs(float("{0:.2f}".format(trial_balance)))
            inst = abs(float("{0:.2f}".format(income_statement)))
            if trba != inst:
                raise Warning(_('Trial balance must match with income statement.'))
            year_result_8999 = self.env['account.account'].search([('code', '=', '8999')])
            year_result_2099 = self.env['account.account'].search([('code', '=', '2099')])
            if not year_result_8999:
                raise Warning(_('Can not find account with code 8999.'))
            if not year_result_2099:
                raise Warning(_('Can not find account with code 2099.'))
            ref = _('Year End %s') %self.fiscalyear_id.name
            end_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('date_stop', '=', self.fiscalyear_id.date_stop)])
            entry = self.env['account.move'].create({
                'journal_id': self.journal_id.id,
                'period_id': end_period.id,
                'date': end_period.date_stop,
                'ref': ref,
            })
            # balance with trial balance
            self.env['account.move.line'].create({
                'name': year_result_2099.name,
                'account_id': year_result_2099.id,
                'debit': 0.0,
                'credit': trba,
                'move_id': entry.id,
            })
            # balance with income statement
            self.env['account.move.line'].create({
                'name': year_result_8999.name,
                'account_id': year_result_8999.id,
                'debit': inst,
                'credit': 0.0,
                'move_id': entry.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_move_form').id,
                'res_id': entry.id,
                'target': 'current',
                'context': {}
            }


class account_initial_entry(models.TransientModel):
    _name = 'account.initial.entry'

    fy_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year to close', required=True, help="Select a Fiscal year to close")
    fy2_id = fields.Many2one(comodel_name='account.fiscalyear', string='New Fiscal Year', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Opening Entries Journal', domain="[('type','=','general')]", required=True, help='The best practice here is to use a journal dedicated to contain the opening entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.')
    period_id = fields.Many2one(comodel_name='account.period', string='Opening Entries Period', required=True)
    report_name = fields.Char(string='Name of new entries', required=True, help="Give name of the new entries")
    equity = fields.Many2one(comodel_name='account.account', string='Equity', required=True)
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('all', 'All Entries')], string='Target Moves')

    @api.one
    @api.onchange('equity')
    def check_equity(self):
        if self.equity.type in ['view', 'consolidation', 'closed']:
            raise Warning(_('You cannot create journal items on an account of type view or consolidation.'))

    @api.multi
    def create_initial_entry(self):
        start_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fy_id.id), ('date_start', '=', self.fy_id.date_start), ('special', '=', True)])
        end_period = self.env['account.period'].search([('fiscalyear_id', '=', self.fy_id.id), ('date_stop', '=', self.fy_id.date_stop)])
        accounts = self.env['account.account'].with_context({'period_from': start_period.id, 'period_to': end_period.id, 'state': self.target_move}).search([('type', 'not in', ['view', 'consolidation', 'closed']), ('user_type.report_type', 'in', ['asset', 'liability']), ('user_type.close_method', '!=', 'none')])
        #1. accounts with defferal method == 'unreconciled'
        accounts_unreconciled = accounts.filtered(lambda a: a.user_type.close_method == 'unreconciled' and a.balance != 0.0)
        #2. accounts with defferal method == 'detail'
        accounts_detail = accounts.filtered(lambda a: a.user_type.close_method == 'detail' and a.balance != 0.0)
        #3. accounts with defferal method == 'balance'
        accounts_balance = accounts.filtered(lambda a: a.user_type.close_method == 'balance' and a.balance != 0.0)
        entry = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'period_id': self.period_id.id,
            'date': self.period_id.date_stop,
            'ref': self.report_name,
        })
        debit = 0.0
        credit = 0.0
        account_list = []
        for acc in accounts_unreconciled | accounts_detail | accounts_balance:
            account_list.append({
                'name': acc.name,
                'account_id': acc.id,
                'debit': abs(float("{0:.2f}".format(acc.balance))) if acc.debit > acc.credit else 0.0,
                'credit': abs(float("{0:.2f}".format(acc.balance))) if acc.credit > acc.debit else 0.0,
            })
            if acc.debit > acc.credit:
                debit += acc.balance
            else:
                credit += acc.balance
        for value in account_list:
            value.update({'move_id': entry.id})
            self.env['account.move.line'].create(value)
        if debit != credit:
            self.env['account.move.line'].create({
                'name': self.equity.name,
                'account_id': self.equity.id,
                'debit': abs(float("{0:.2f}".format(debit+credit))) if debit+credit < 0.0 else 0.0,
                'credit': abs(float("{0:.2f}".format(debit+credit))) if debit+credit > 0.0 else 0.0,
                'move_id': entry.id
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_id': entry.id,
            'target': 'current',
            'context': {}
        }
