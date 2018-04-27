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


# order must be correct:
TAGS = [
    'LonBrutto',
    'Forman',
    'AvdrKostn',
    'SumUlagAvg',
    'UlagAvgHel',
    'AvgHel',
    'UlagAvgAldersp',
    'AvgAldersp',
    'UlagAlderspSkLon',
    'AvgAlderspSkLon',
    'UlagSkLonSarsk',
    'SkLonSarsk',
    'UlagAvgAmbassad',
    'AvgAmbassad',
    'UlagAvgAmerika',
    'AvgAmerika',
    'UlagStodForetag',
    'AvdrStodForetag',
    'UlagStodUtvidgat',
    'AvdrStodUtvidgat',
    'SumAvgBetala',
    'UlagSkAvdrLon',
    'SkAvdrLon',
    'UlagSkAvdrPension',
    'SkAvdrPension',
    'UlagSkAvdrRanta',
    'SkAvdrRanta',
    'UlagSumSkAvdr',
    'SumSkAvdr',
    'SjukLonKostnEhs'
]

class agd_declaration_wizard(models.TransientModel):
    _name = 'agd.declaration.wizard'

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Räkenskapsår', help='Håll tom för alla öppna räkenskapsår', default=_get_year)
    period = fields.Many2one(comodel_name='account.period', string='Period', required=True)
    baskonto = fields.Float(string='Baskonto', default=0.0, readonly=True, help='Avläsning av transationer från baskontoplanen.')
    agavgpres = fields.Float(string='Arbetsgivaravgift & Preliminär skatt', default=0.0, readonly=True)
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], string='Target Moves')
    free_text = fields.Text(string='Upplysningstext')
    eskd_file = fields.Binary(compute='_compute_eskd_file')
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat')

    @api.one
    def _compute_eskd_file(self):
        # account should not included: AgBrutU, AgAvgU, AgAvgAv, AgAvg, AgAvd, AgAvdU, AgAvgPreS, AgPre, UlagVXLon, AvgVXLon
        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('l10n_se.tax_group_hr').id), ('name', 'not in', ['eSKDUpload', 'Ag', 'AgBrutU', 'AgAvgU', 'AgAvgAv', 'AgAvg', 'AgAvd', 'AgAvdU', 'AgAvgPreS', 'AgPre', 'UlagVXLon', 'AvgVXLon'])])
        def parse_xml(recordsets):
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = self.env.user.company_id.company_registry
            ag = etree.SubElement(root, 'Ag')
            period = etree.SubElement(ag, 'Period')
            period.text = self.period.date_start[:4] + self.period.date_start[5:7]
            for tag in TAGS:
                tax = etree.SubElement(ag, tag)
                acc = self.env['account.tax'].search([('name', '=', tag)])
                if acc:
                    tax.text = str(int(abs(acc.with_context({'period_id': self.period.id, 'state': self.target_move}).sum_period)))
                else:
                    tax.text = '0'
            free_text = etree.SubElement(ag, 'TextUpplysningAg')
            free_text.text = self.free_text or ''
            return root
        xml = etree.tostring(parse_xml(tax_account), pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        self.eskd_file = base64.b64encode(xml)

    @api.multi
    def create_eskd(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            #for v9.0, 10.0
            'report_file': '/web/content/agd.declaration.wizard/%s/eskd_file/%s?download=true' %(self.id, 'ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]))
            #for v7.0, v8.0
            #'report_file': '/web/binary/saveas?model=agd.declaration.wizard&field=eskd_file&filename_field=%s&id=%s' %('ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]), self.id)
        }

    @api.onchange('period', 'target_move')
    def read_account(self):
        if self.period:
            tax_account = self.env['account.tax'].with_context({'period_id': self.period.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
            if tax_account:
                self.agavgpres = tax_account.sum_period
                sum_baskonto = 0.0
                for account in self.env['account.financial.report'].search([('tax_ids', 'in', tax_account.mapped('children_tax_ids').mapped('id'))]).mapped('account_ids'):
                    sum_baskonto += account.get_balance(self.period, self.target_move)
                self.baskonto = sum_baskonto

    @api.multi
    def create_entry(self):
        tax_accounts = self.env['account.tax'].with_context({'period_id': self.period.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
        kontoskatte = self.env['account.account'].with_context({'period_from': self.period.id, 'period_to': self.period.id}).search([('id', 'in', self.env['account.financial.report'].search([('tax_ids', 'in', tax_accounts.mapped('children_tax_ids').mapped('id'))]).mapped('account_ids').mapped('id'))])
        agd_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.agd_journal')
        if not agd_journal_id:
            raise Warning('Konfigurera din arbetsgivardeklaration journal!')
        else:
            agd_journal = self.env['account.journal'].browse(int(agd_journal_id))
            skattekonto = agd_journal.default_debit_account_id
            if len(kontoskatte) > 0 and skattekonto:
                total = 0.0
                entry = self.env['account.move'].create({
                    'journal_id': agd_journal.id,
                    'period_id': self.period.id,
                    'date': fields.Date.today(),
                    'ref': u'Arbetsgivardeklaration',
                })
                if entry:
                    move_line_list = []
                    for k in kontoskatte:
                        credit = k.get_debit_credit_balance(self.period, self.target_move).get('credit')
                        if credit != 0.0:
                            move_line_list.append((0, 0, {
                                'name': k.name,
                                'account_id': k.id,
                                'debit': credit,
                                'credit': 0.0,
                                'move_id': entry.id,
                            }))
                            total += credit
                    move_line_list.append((0, 0, {
                        'name': skattekonto.name,
                        'account_id': skattekonto.id,
                        'partner_id': self.env.ref('base.res_partner-SKV').id,
                        'debit': 0.0,
                        'credit': total,
                        'move_id': entry.id,
                    }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id}) # wizard disappeared
            else:
                raise Warning(_('kontoskatte: %sst, skattekonto: %s') %(len(kontoskatte), skattekonto))

    @api.multi
    def show_entry(self):
        if not self.move_id:
            raise Warning(_(u'Du måste skapa verifikat först'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_id': self.move_id.id,
            'target': 'new',
            'context': {}
        }

    @api.multi
    def show_account_moves(self):
        tax_accounts = self.env['account.tax'].with_context({'period_id': self.period.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
        domain = [('move_id.period_id', '=', self.period.id), ('account_id', 'in', self.env['account.financial.report'].search([('tax_ids', 'in', tax_accounts.mapped('children_tax_ids').mapped('id'))]).mapped('account_ids').mapped('id'))]
        if self.target_move in ['draft', 'posted']:
            domain.append(('move_id.state', '=', self.target_move))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env.ref('account.view_move_line_tree').id,
            'target': 'current',
            'domain': domain,
            'context': {'search_default_period_id': self.period.id},
        }

    @api.multi
    def show_journal_items(self):
        return self.show_account_moves()

    @api.multi
    def print_report(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'accounting.report',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('account.accounting_report_view').id,
            'target': 'new',
            'domain': [],
            'context': {
                'default_account_report_id': self.env.ref('l10n_se_tax_report.agd_report').id,
                'default_date_from': self.period.date_start,
                'default_date_to': self.period.date_stop,
            },
        }

        #~ account_tax_codes = self.env['account.tax'].search([])
        #~ data = {}
        #~ data['ids'] = account_tax_codes.mapped('id')
        #~ data['model'] = 'account.tax'
        #~ return self.env['report'].with_context({'period_id': self.period.id, 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_tax_report.ag_report_glabel').name, data=data)
