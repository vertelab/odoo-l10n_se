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


NAMEMAPPING = {
    u'MP1': u'MomsUtgHog',
    u'MP2': u'MomsUtgMedel',
    u'MP3': u'MomsUtgLag',
    u'I': u'MomsInkopUtgHog',
    u'I12': u'MomsInkopUtgMedel',
    u'I6': u'MomsInkopUtgLag',
    u'MBBUI': u'MomsUlagImport',
    u'U1MBBUI': u'MomsImportUtgHog',
    u'U2MBBUI': u'MomsImportUtgMedel',
    u'U3MBBUI': u'MomsImportUtgLag',
    u'MPFF': u'HyrinkomstFriv',
    u'VTEU': u'ForsVaruAnnatEg',
    u'E': u'ForsVaruUtomEg',
    u'OMSS': u'ForsKopareSkskSverige',
    u'FTEU': u'ForsTjOvrUtomEg',
    u'VFEU': u'InkopVaruAnnatEg',
    u'TFEU': u'InkopTjanstAnnatEg',
    u'TFFU': u'InkopTjanstUtomEg',
    u'IVIS': u'InkopVaruSverige',
    u'ITIS': u'InkopTjanstSverige',
    u'3VEU': u'InkopVaruMellan3p',
    u'3FEU': u'ForsTjSkskAnnatEg',
}

TAXNOTINCLUD = [u'MP1i', u'MP2i', u'MP3i', u'Ii', u'I12i', u'I6i']

class moms_declaration_wizard(models.TransientModel):
    _name = 'moms.declaration.wizard'

    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Räkenskapsår', help='Håll tom för alla öppna räkenskapsår', default=_get_year)
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True)
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period', required=True)
    baskonto = fields.Float(string='Baskonto', default=0.0, readonly=True, help='Avläsning av transationer från baskontoplanen.')
    br1 = fields.Float(string='Moms att betala ut (+) eller få tillbaka (-)', default=0.0, readonly=True, help='Avläsning av skattekonto.')
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], string='Target Moves')
    free_text = fields.Text(string='Upplysningstext')
    eskd_file = fields.Binary(compute='_compute_eskd_file')
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat', readonly=True)

    @api.one
    def _compute_eskd_file(self):
        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id), ('name', 'not in', TAXNOTINCLUD)])
        def parse_xml(recordsets):
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = self.env.user.company_id.company_registry
            moms = etree.SubElement(root, 'Moms')
            period = etree.SubElement(moms, 'Period')
            period.text = self.period_start.date_start[:4] + self.period_start.date_start[5:7]
            for record in recordsets:
                tax = etree.SubElement(moms, NAMEMAPPING.get(record.name) or record.name) # TODO: make sure all account.tax name exist here, removed "or" later on
                tax.text = str(int(abs(record.with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id, 'state': self.target_move}).sum_period)))
            free_text = etree.SubElement(moms, 'TextUpplysningMoms')
            free_text.text = self.free_text or ''
            return root
        xml = etree.tostring(parse_xml(tax_account), pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www1.skatteverket.se/demoeskd/eSKDUpload_6p0.dtd">')
        self.eskd_file = base64.b64encode(xml)

    @api.multi
    def create_eskd(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            #for v9.0, 10.0
            'report_file': '/web/content/moms.declaration.wizard/%s/eskd_file/%s?download=true' %(self.id, 'moms-%s.txt' %(self.period_start.date_start[:4] + self.period_start.date_start[5:7]))
            #for v7.0, v8.0
            #'report_file': '/web/binary/saveas?model=moms.declaration.wizard&field=eskd_file&filename_field=%s&id=%s' %('ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]), self.id)
        }

    def get_period_ids(self, period_start, period_stop):
        if period_stop and period_stop.date_start < period_start.date_start:
            raise Warning('Stop period must be after start period')
        if period_stop.date_start == period_start.date_start:
            return [period_start.id]
        else:
            return [r.id for r in self.env['account.period'].search([('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop)])]

    def _get_account_period_balance(self, account, period_start, period_stop, target_move):
        return sum(account.get_balance(period, target_move) for period in self.env['account.period'].browse(self.get_period_ids(self.period_start, self.period_stop)))

    @api.onchange('period_start', 'period_stop', 'target_move')
    def read_account(self):
        if self.period_start and self.period_stop:
            tax_account = 0.0
            for p in self.get_period_ids(self.period_start, self.period_stop):
                tax_account += sum(self.env['account.tax'].with_context({'period_id': p, 'state': self.target_move}).search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id)]).mapped('sum_period'))
            self.br1 = tax_account
        sum_baskonto = 0.0
        for account in self.env.ref('l10n_se_tax_report.49').mapped('account_ids'):
            sum_baskonto += self._get_account_period_balance(account, self.period_start, self.period_stop, self.target_move)
        self.baskonto = sum_baskonto

    @api.multi
    def create_entry(self):
        kontomoms = self.env.ref('l10n_se_tax_report.49').mapped('account_ids')
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
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                })
                if entry:
                    move_line_list = []
                    for k in kontomoms: # kollar på 26xx konton
                        balance = self._get_account_period_balance(k, self.period_start, self.period_stop, self.target_move)
                        if balance > 0.0: # ingående moms
                            move_line_list.append((0, 0, {
                                'name': k.name,
                                'account_id': k.id,
                                'credit': balance,
                                'debit': 0.0,
                                'move_id': entry.id,
                            }))
                        if balance < 0.0: # utgående moms
                            move_line_list.append((0, 0, {
                                'name': k.name,
                                'account_id': k.id,
                                'debit': abs(balance),
                                'credit': 0.0,
                                'move_id': entry.id,
                            }))
                        total += balance
                    if total > 0.0: # momsfordran, moms ska få tillbaka
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id, # moms_journal.default_debit_account_id
                            'partner_id': '',
                            'debit': total,
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id,
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': total,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': total,
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                    if total < 0.0: # moms redovisning, moms ska betalas in
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id, # moms_journal.default_credit_account_id
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': abs(total),
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id,
                            'partner_id': '',
                            'debit': abs(total),
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': 0.0,
                            'credit': abs(total),
                            'move_id': entry.id,
                        }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id}) # wizard disappeared
        else:
            raise Warning(_('Kontomoms: %sst, momsskuld: %s, momsfordran: %s, skattekonto: %s') %(len(kontomoms), momsskuld, momsfordran, skattekonto))

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
        tax_accounts = self.env.ref('l10n_se_tax_report.49').mapped('account_ids').with_context({'state': self.target_move})
        domain = [('account_id', 'in', tax_accounts.mapped('id')), ('move_id.period_id', 'in', self.get_period_ids(self.period_start, self.period_stop))]
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
            'context': {},
        }

    @api.multi
    def show_journal_items(self):
        tax_accounts = self.env['account.tax'].with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id, 'state': self.target_move}).search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id)])
        domain = [('move_id.period_id', 'in', self.get_period_ids(self.period_start, self.period_stop)), ('account_id', 'in', tax_accounts.mapped('id'))]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': self.env.ref('account.view_move_line_tree').id,
            'target': 'current',
            'domain': domain,
            'context': {},
        }

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
                'default_account_report_id': self.env.ref('l10n_se_tax_report.root').id,
                'default_date_from': self.period_start.date_start,
                'default_date_to': self.period_stop.date_stop,
            },
        }

        #~ account_tax_codes = self.env['account.tax'].search([])
        #~ data = {}
        #~ data['ids'] = account_tax_codes.mapped('id')
        #~ data['model'] = 'account.tax'
        #~ return self.env['report'].with_context({'period_ids': self.get_period_ids(self.period_start, self.period_stop), 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_tax_report.moms_report_glabel').name, data=data)
