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
from lxml import etree
import base64
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class agd_declaration_wizard(models.TransientModel):
    _name = 'agd.declaration.wizard'

    @api.model
    def get_tax_account_domain(self):
        return [('user_type_id', '=', self.env['account.account.type'].search([('type', '=', 'payable')]).id)]

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year', default=_get_year)
    period = fields.Many2one(comodel_name='account.period', string='Period', required=True)
    skattekonto = fields.Float(string='Skattekontot', default=0.0, readonly=True)
    agavgpres = fields.Float(string='Arbetsgivaravgift & Preliminär skatt', default=0.0, readonly=True)
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], string='Target Moves')
    eskd_file = fields.Binary(compute='_compute_eskd_file')

    @api.one
    def _compute_eskd_file(self):
        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('l10n_se.tax_group_hr').id), ('name', 'not in', ['eSKDUpload', 'Ag'])])
        def parse_xml(recordsets):
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = self.env.user.company_id.company_registry
            ag = etree.SubElement(root, 'Ag')
            period = etree.SubElement(ag, 'Period')
            period.text = self.period.date_start[:4] + self.period.date_start[5:7]
            for record in recordsets:
                tax = etree.SubElement(ag, record.name)
                tax.text = str(int(abs(record.with_context({'period_id': self.period.id, 'state': self.target_move}).sum_period)))
            return root
        xml = etree.tostring(parse_xml(tax_account), pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www1.skatteverket.se/demoeskd/eSKDUpload_6p0.dtd">')
        self.eskd_file = base64.b64encode(xml)

    #~ ej_bokforda = fields.Boolean(string='Ej bokförda', default=True)

    #~ def _build_comparison_context(self, cr, uid, ids, data, context=None):
        #~ if context is None:
            #~ context = {}
        #~ result = {}
        #~ result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
        #~ result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        #~ result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        #~ result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        #~ if data['form']['filter_cmp'] == 'filter_date':
            #~ result['date_from'] = data['form']['date_from_cmp']
            #~ result['date_to'] = data['form']['date_to_cmp']
        #~ elif data['form']['filter_cmp'] == 'filter_period':
            #~ if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
                #~ raise osv.except_osv(_('Error!'),_('Select a starting and an ending period'))
            #~ result['period_from'] = data['form']['period_from_cmp']
            #~ result['period_to'] = data['form']['period_to_cmp']
        #~ return result

    @api.onchange('period', 'target_move')
    def read_account(self):
        if self.period:
            tax_accounts = self.env['account.account'].with_context({'period_from': self.period.id, 'period_to': self.period.id}).search(self.get_tax_account_domain())
            tax_account = self.env['account.tax'].with_context({'period_id': self.period.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
            #~ self.skattekonto = sum(tax_accounts.mapped('balance'))
            if tax_account:
                self.agavgpres = tax_account.sum_period

    @api.multi
    def create_entry(self):
        kontoskatte = self.env['account.account'].with_context({'period_from': self.period.id, 'period_to': self.period.id}).search(self.get_tax_account_domain())
        skattekonto = self.env['account.account'].search([('code', '=', '1630')])
        if len(kontoskatte) > 0 and skattekonto:
            agd_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_report.agd_journal')
            if not agd_journal_id:
                raise Warning('Konfigurera din arbetsgivardeklaration journal!')
            else:
                total = 0.0
                entry = self.env['account.move'].create({
                    'journal_id': self.env.ref('l10n_se.lonjournal').id,
                    'period_id': self.period.id,
                    'date': fields.Date.today(),
                })
                if entry:
                    for k in kontoskatte:
                        credit = k.get_debit_credit_balance(self.period, self.period).get('credit')
                        if credit != 0.0:
                            self.env['account.move.line'].create({
                                'name': k.name,
                                'account_id': k.id,
                                'debit': credit,
                                'credit': 0.0,
                                'move_id': entry.id,
                            })
                            total += credit
                    self.env['account.move.line'].create({
                        'name': skattekonto.name,
                        'account_id': skattekonto.id,
                        'partner_id': self.env.ref('base.res_partner-SKV').id,
                        'debit': 0.0,
                        'credit': total,
                        'move_id': entry.id,
                    })
                    #~ return self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_journal_period_tree')
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
        else:
            raise Warning(_('kontoskatte: %sst, skattekonto: %s') %(len(kontoskatte), skattekonto))

    @api.multi
    def create_eskd(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            #for v9.0, 10.0
            'report_file': '/web/content/agd.declaration.wizard/%s/eskd_file/%s?download=true' %(self.id, 'ag-%s.txt' %self.period.date_start[:4])
            #for v7.0, v8.0
            #'report_file': '/web/binary/saveas?model=agd.declaration.wizard&field=eskd_file&filename_field=%s&id=%s' %('ag-%s.txt' %self.period.date_start[:4], self.id)
        }

    @api.multi
    def show_account_moves(self):
        tax_accounts = self.env['account.account'].search(self.get_tax_account_domain())
        domain = [('account_id', 'in', tax_accounts.mapped('id'))]
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
            'context': {'search_default_period_id': self.period.id}
        }

    @api.multi
    def show_journal_items(self):
        tax_account = self.env['account.tax'].search([('name', '=', 'AgAvgPreS')])
        domain = [('tax_code_id', 'child_of', tax_account.id)]
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
            'context': {'search_default_period_id': self.period.id}
        }

    @api.multi
    def print_report(self):
        account_tax_codes = self.env['account.tax'].search([])
        data = {}
        data['ids'] = account_tax_codes.mapped('id')
        data['model'] = 'account.tax'

        return self.env['report'].with_context({'period_id': self.period.id, 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_report.ag_report_glabel').name, data=data)
