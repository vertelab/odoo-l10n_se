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

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class moms_declaration_wizard(models.TransientModel):
    _name = 'moms.declaration.wizard'

    @api.model
    def get_tax_account_domain(self):
        return [('parent_id', '=', self.env['account.account'].search([('code', 'in', ['26','B14'])]).id), ('code', 'not in', ['2650', '1650', '1630']), ('user_type_id', '=', self.env['account.account.type'].search([('type', '=', 'liability'), ('close_method', '=', 'none')]).id)]

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year', default=_get_year)
    period_start = fields.Many2one(comodel_name='account.period', string='Start Period', required=True)
    period_stop = fields.Many2one(comodel_name='account.period', string='End Period', required=True)
    skattekonto = fields.Float(string='Skattekontot', default=0.0, readonly=True, help='Sum of all transactions on account of type tax.')
    br1 = fields.Float(string='Moms att betala ut (+) eller få tillbaka (-)', default=0.0, readonly=True, help='Sum of all tax accounts. Without any payments to tax office.')
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], string='Target Moves')
    free_text = fields.Text(string='Text Upplysning')
    eskd_file = fields.Binary(compute='_compute_eskd_file')

    @api.one
    def _compute_eskd_file(self):
        # TODO: find all account.tax with tax_group_id self.env.ref('account.tax_group_taxes').id
        # make a mapping dictionary and find eSKD tags
        self.eskd_file = None

    @api.multi
    def create_eskd(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            #for v9.0, 10.0
            'report_file': '/web/content/moms.declaration.wizard/%s/eskd_file/%s?download=true' %(self.id, 'ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]))
            #for v7.0, v8.0
            #'report_file': '/web/binary/saveas?model=moms.declaration.wizard&field=eskd_file&filename_field=%s&id=%s' %('ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]), self.id)
        }

    def get_period_ids(self, period_start, period_stop):
        if period_stop.date_start < period_start.date_start:
            raise Warning('Stop period must be after start period')
        if period_stop.date_start == period_start.date_start:
            return [period_start.id]
        else:
            return [r.id for r in self.env['account.period'].search([('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop)])]

    @api.onchange('period_start', 'period_stop', 'target_move')
    def read_account(self):
        if self.period_start and self.period_stop:
            tax_account = 0.0
            for p in self.get_period_ids(self.period_start, self.period_stop):
                tax_account += sum(self.env['account.tax'].with_context({'period_id': p, 'state': self.target_move}).search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id)]).mapped('sum_period'))
            self.br1 = tax_account

    @api.multi
    def create_vat(self):
        kontomoms = self.env['account.account'].with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id, 'state': self.target_move}).search(self.get_tax_account_domain())
        momsskuld = self.env['account.account'].search([('code', '=', '2650')])
        momsfordran = self.env['account.account'].search([('code', '=', '1650')])
        skattekonto = self.env['account.account'].search([('code', '=', '1630')])
        if len(kontomoms) > 0 and momsskuld and momsfordran and skattekonto:
            total = 0.0
            moms_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_report.moms_journal')
            if not moms_journal_id:
                raise Warning('Konfigurera din momsdeklaration journal!')
            else:
                moms_journal = self.env['account.journal'].browse(moms_journal_id)
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
                    if total > 0.0: # momsfordran, moms ska få tillbaka
                        self.env['account.move.line'].create({
                            'name': momsfordran.name,
                            'account_id': momsfordran.id, # moms_journal.default_debit_account_id
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
                    if total < 0.0: # moms redovisning, moms ska betalas in
                        self.env['account.move.line'].create({
                            'name': momsskuld.name,
                            'account_id': momsskuld.id, # moms_journal.default_credit_account_id
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
        else:
            raise Warning(_('Kontomoms: %sst, momsskuld: %s, momsfordran: %s, skattekonto: %s') %(len(kontomoms), momsskuld, momsfordran, skattekonto))


    @api.multi
    def show_account_moves(self):
        tax_accounts = self.env['account.account'].search(self.get_tax_account_domain())
        domain = [('account_id', 'in', tax_accounts.mapped('id')), ('period_id', 'in', self.get_period_ids(self.period_start, self.period_stop))]
        if self.target_move in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self.target_move))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': domain,
            'context': {}
        }

    @api.multi
    def show_journal_items(self):
        tax_account = self.env['account.tax'].search([('name', 'in', ['aR1','bR1','R1'])])
        domain = [('tax_code_id', 'child_of', tax_account.id), ('period_id', 'in', self.get_period_ids(self.period_start, self.period_stop))]
        if self.target_move in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self.target_move))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env['ir.model.data'].get_object_reference('account', 'view_move_line_tree')[1],
            'target': 'current',
            'domain': domain,
            'context': {}
        }

    @api.multi
    def print_report(self):
        account_tax_codes = self.env['account.tax'].search([])
        data = {}
        data['ids'] = account_tax_codes.mapped('id')
        data['model'] = 'account.tax'

        return self.env['report'].with_context({'period_ids': self.get_period_ids(self.period_start, self.period_stop), 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_tax_report.moms_report_glabel').name, data=data)
