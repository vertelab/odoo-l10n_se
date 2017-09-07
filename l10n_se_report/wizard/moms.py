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


class account_tax_code(models.Model):
    _inherit = 'account.tax.code'

    sum_period = fields.Float(string='Period Sum', compute='_sum_periods')

    @api.one
    def _sum_periods(self):
        if self._context.get('period_ids', False):
            move_state = ('posted', )
            if self._context.get('state', False) == 'all':
                move_state = ('draft', 'posted', )
            period_ids = tuple(self._context['period_ids'])
            self.sum_period = self._sum(None, None,
                where=' AND line.period_id IN %s AND move.state IN %s', where_params=(period_ids, move_state))[self.id]
        else:
            self.sum_period = super(account_tax_code, self)._sum_period(None, None)[self.id]


class moms_declaration_wizard(models.TransientModel):
    _name = 'moms.declaration.wizard'

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax.code'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    chart_tax_id = fields.Many2one(comodel_name='account.tax.code', string='Chart of Tax', help='Select Charts of Taxes', default=_get_tax, required=True, domain = [('parent_id','=', False)])
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year', default=_get_year)
    period_start = fields.Many2one(comodel_name='account.period', string='Period', required=True)
    period_stop = fields.Many2one(comodel_name='account.period', string='Period', required=True)
    skattekonto = fields.Float(string='Skattekontot', default=0.0, readonly=True)
    br1 = fields.Float(string='Moms att betala ut eller få tillbaka', default=0.0, readonly=True)

    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
        elif data['form']['filter_cmp'] == 'filter_period':
            if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
                raise osv.except_osv(_('Error!'),_('Select a starting and an ending period'))
            result['period_from'] = data['form']['period_from_cmp']
            result['period_to'] = data['form']['period_to_cmp']
        return result

    def get_period_ids(self, period_start, period_stop):
        if period_stop.date_start < period_start.date_start:
            raise Warning('Stop period must be after start period')
        if period_stop.date_start == period_start.date_start:
            return [period_start.id]
        else:
            return [r.id for r in self.env['account.period'].search([('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop)])]

    @api.one
    @api.onchange('period_start', 'period_stop')
    def read_account(self):
        # kollar ej boförd
        if self.period_start and self.period_stop:
            tax_accounts = self.env['account.account'].with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id}).search([('parent_id', '=', self.env['account.account'].search([('code', '=', '26')]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
            self.skattekonto = sum(tax_accounts.mapped('balance'))
            tax_account = 0.0
            for p in self.get_period_ids(self.period_start, self.period_stop):
                tax_account += self.env['account.tax.code'].with_context({'period_id': p, 'state': 'all'}).search([('code', '=', 'bR1')]).sum_period
            self.br1 = tax_account

    @api.multi
    def create_vat(self):
        kontomoms = self.env['account.account'].with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id}).search([('parent_id', '=', self.env['account.account'].search([('code', '=', '26')]).id), ('code', '!=', '2650'), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        momsskuld = self.env['account.account'].search([('code', '=', '2650')])
        momsfordran = self.env['account.account'].search([('code', '=', '1650')])
        skattekonto = self.env['account.account'].search([('code', '=', '1630')])
        if len(kontomoms) > 0 and momsskuld and momsfordran and skattekonto:
            total = 0.0
            #~ moms_journal_id = self.env['ir.config_parameter'].get_param('account.moms_journal')
            moms_journal = self.env['account.journal'].browse(5)
            if not moms_journal:
                raise Warning('Konfigurera din momsdeklaration journal!')
            else:
                vat = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                })
                if vat:
                    for k in kontomoms: # kollar på 26xx konton
                        if k.balance > 0.0: # ingående moms
                            self.env['account.move.line'].create({
                                'name': k.name,
                                'account_id': k.id,
                                'credit': k.balance,
                                'debit': 0.0,
                                'move_id': vat.id,
                            })
                        if k.balance < 0.0: # utgående moms
                            self.env['account.move.line'].create({
                                'name': k.name,
                                'account_id': k.id,
                                'debit': abs(k.balance),
                                'credit': 0.0,
                                'move_id': vat.id,
                            })
                        total += k.balance
                    if total < 0.0: # moms redovisning
                        self.env['account.move.line'].create({
                            'name': momsskuld.name,
                            'account_id': momsskuld.id,
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': abs(total),
                            'move_id': vat.id,
                        })
                        self.env['account.move.line'].create({
                            'name': momsskuld.name,
                            'account_id': momsskuld.id,
                            'partner_id': '',
                            'debit': abs(total),
                            'credit': 0.0,
                            'move_id': vat.id,
                        })
                        self.env['account.move.line'].create({
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': 0.0,
                            'credit': abs(total),
                            'move_id': vat.id,
                        })
                    if total > 0.0: # momsfordran
                        self.env['account.move.line'].create({
                            'name': momsfordran.name,
                            'account_id': momsfordran.id,
                            'partner_id': '',
                            'debit': total,
                            'credit': 0.0,
                            'move_id': vat.id,
                        })
                        self.env['account.move.line'].create({
                            'name': momsfordran.name,
                            'account_id': momsfordran.id,
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': total,
                            'move_id': vat.id,
                        })
                        self.env['account.move.line'].create({
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': total,
                            'credit': 0.0,
                            'move_id': vat.id,
                        })

                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.move',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': self.env.ref('account.view_move_form').id,
                        'res_id': vat.id,
                        'target': 'current',
                        'context': {}
                    }

    @api.multi
    def show_account_moves(self):
        tax_accounts = self.env['account.account'].search([('parent_id', '=', self.env['account.account'].search([('code', '=', '26')]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': [('account_id', 'in', tax_accounts.mapped('id')), ('period_id', 'in', self.get_period_ids(self.period_start, self.period_stop))],
            'context': {}
        }

    @api.multi
    def show_journal_items(self):
        tax_account = self.env['account.tax.code'].search([('code', '=', 'bR1')])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': [('tax_code_id', 'child_of', tax_account.id), ('state', '<>', 'draft'), ('period_id', 'in', self.get_period_ids(self.period_start, self.period_stop))],
            'context': {}
        }

    @api.multi
    def print_report(self):
        account_tax_codes = self.env['account.tax.code'].search([])
        data = {}
        data['ids'] = account_tax_codes.mapped('id')
        data['model'] = 'account.tax.code'

        return self.env['report'].with_context({'period_ids': self.get_period_ids(self.period_start, self.period_stop), 'state': 'all'}).get_action(account_tax_codes, self.env.ref('l10n_se_report.moms_report_glabel').name, data=data)
