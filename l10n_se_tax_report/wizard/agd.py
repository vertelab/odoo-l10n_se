# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
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


class agd_declaration_wizard(models.TransientModel):
    _name = 'agd.declaration.wizard'

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax.code'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    chart_tax_id = fields.Many2one(comodel_name='account.tax.code', string='Chart of Tax', help='Select Charts of Taxes', default=_get_tax, required=True, domain = [('parent_id','=', False)])
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year', default=_get_year)
    period = fields.Many2one(comodel_name='account.period', string='Period', required=True)
    skattekonto = fields.Float(string='Skattekontot', default=0.0, readonly=True)
    agavgpres = fields.Float(string='Arbetsgivaravgift & Preliminär skatt', default=0.0, readonly=True)
    ej_bokforda = fields.Boolean(string='Ej bokförda', default=True)

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

    @api.one
    @api.onchange('period')
    def read_account(self):
        if self.period:
            tax_accounts = self.env['account.account'].with_context({'period_from': self.period.id, 'period_to': self.period.id}).search([('parent_id', '=', self.env['account.account'].search([('code', '=', '27')]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
            tax_account = self.env['account.tax.code'].with_context({'period_id': self.period.id, 'state': 'all'}).search([('code', '=', 'AgAvgPreS')])
            self.skattekonto = sum(tax_accounts.mapped('credit'))
            if tax_account:
                #~ self.agavgpres = sum(self.env['account.move.line'].search([('tax_code_id', 'child_of', tax_account.id), ('account_id', 'in', tax_accounts.mapped('id')), ('move_id.state', '=', 'draft'), ('state', '=', 'valid'), ('period_id', '=', self.period.id)]).mapped('credit'))
                self.agavgpres = tax_account.sum_period

    @api.multi
    def create_vat(self):
        kontoskatte = self.env['account.account'].with_context({'period_from': self.period.id, 'period_to': self.period.id}).search([('parent_id', '=', self.env['account.account'].search([('code', '=', '27')]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        skattekonto = self.env['account.account'].search([('code', '=', '1630')])
        if len(kontoskatte) > 0 and skattekonto:
            agd_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_report.agd_journal')
            if not agd_journal_id:
                raise Warning('Konfigurera din arbetsgivardeklaration journal!')
            else:
                total = 0.0
                vat = self.env['account.move'].create({
                    'journal_id': self.env.ref('l10n_se.lonjournal').id,
                    'period_id': self.period.id,
                    'date': fields.Date.today(),
                })
                if vat:
                    for k in kontoskatte:
                        if k.credit != 0.0:
                            self.env['account.move.line'].create({
                                'name': k.name,
                                'account_id': k.id,
                                'debit': k.credit,
                                'credit': 0.0,
                                'move_id': vat.id,
                            })
                            total += k.credit
                    self.env['account.move.line'].create({
                        'name': skattekonto.name,
                        'account_id': skattekonto.id,
                        'partner_id': self.env.ref('base.res_partner-SKV').id,
                        'debit': 0.0,
                        'credit': total,
                        'move_id': vat.id,
                    })
                    #~ return self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_journal_period_tree')
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
        tax_accounts = self.env['account.account'].search([('parent_id', '=', self.env['account.account'].search([('code', '=', '27')]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        domain = [('account_id', 'in', tax_accounts.mapped('id'))]
        if self.ej_bokforda:
            domain.append(('move_id.state', '=', 'draft'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': domain,
            'context': {'search_default_period_id': self.period.id}
        }

    @api.multi
    def show_journal_items(self):
        tax_account = self.env['account.tax'].search([('name', '=', 'AgAvgPreS')])
        domain = [('tax_code_id', 'child_of', tax_account.id)]
        if self.ej_bokforda:
            domain.append(('move_id.state', '=', 'draft'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': domain,
            'context': {'search_default_period_id': self.period.id}
        }

    @api.multi
    def print_report(self):
        account_tax_codes = self.env['account.tax'].search([])
        data = {}
        data['ids'] = account_tax_codes.mapped('id')
        data['model'] = 'account.tax'

        return self.env['report'].with_context({'period_id': self.period.id, 'state': 'all'}).get_action(account_tax_codes, self.env.ref('l10n_se_report.ag_report_glabel').name, data=data)
