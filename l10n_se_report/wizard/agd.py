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


class agd_declaration_wizard(models.TransientModel):
    _name = 'agd.declaration.wizard'
    
    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax.code'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    chart_tax_id = fields.Many2one(comodel_name='account.tax.code', string='Chart of Tax', help='Select Charts of Taxes', default=_get_tax, required=True, domain = [('parent_id','=', False)])
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year')
    period = fields.Many2one(comodel_name='account.period', string='Period')
    skattekonto = fields.Float(string='Skattekontot', default=0.0, readonly=True)
    agavgpres = fields.Float(string='Arbetsgivaravgift & Preliminär skatt', default=0.0, readonly=True)
    
    @api.one
    @api.onchange('period')
    def read_account(self):
        tax_accounts = self.env['account.account'].search([('parent_id', '=', self.env['account.account'].search([('code', '=', 27)]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        moves = self.env['account.move'].search([('period_id', '=', self.period.id), ('state', '=', 'draft')]).mapped('id')
        tax_account = self.env['account.tax.code'].search([('code', '=', 'AgAvgPreS')])
        if len(moves) > 0:
            self.skattekonto = sum(self.env['account.move.line'].search([('move_id', 'in', moves), ('account_id', 'in', tax_accounts.mapped('id')), ('move_id.state', '=', 'draft'), ('state', '=', 'valid')]).mapped('credit'))
        if tax_account:
            self.agavgpres = sum(self.env['account.move.line'].search([('tax_code_id', 'child_of', tax_account.id), ('account_id', 'in', tax_accounts.mapped('id')), ('move_id.state', '=', 'draft'), ('state', '=', 'valid'), ('period_id', '=', self.period.id)]).mapped('credit'))
    
    @api.one
    def create_vat(self):
        kontoskatte = self.env['account.account'].search([('parent_id', '=', self.env['account.account'].search([('code', '=', 27)]).id), ('user_type', '=', self.env['account.account.type'].search([('code', '=', 'tax')]).id)])
        skattekonto = self.env['account.account'].search([('code', '=', 1630)])
        if len(kontoskatte) > 0 and skattekonto:
            total = 0.0
            vat = self.env['account.move'].create({
                'journal_id': self.env.ref('l10n_se.lonjournal').id,
                'period_id': self.period.id,
                'date': fields.Date.today(),
            })
            if vat:
                for k in kontoskatte:
                    if k.credit != 0.0:
                        self.env['account.move.line'].with_context({'get_start_period': self.period}).create({
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

