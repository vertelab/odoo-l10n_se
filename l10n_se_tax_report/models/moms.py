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
from collections import OrderedDict
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


# order must be correct
NAMEMAPPING = OrderedDict([
    ('ForsMomsEjAnnan', []),                #05: Momspliktig försäljning som inte ingår i annan ruta nedan
    ('UttagMoms', ['MU1', 'MU2', 'MU3']),   #06: Momspliktiga uttag
    ('UlagMargbesk', ['MBBU']),             #07: Beskattningsunderlag vid vinstmarginalbeskattning
    ('HyrinkomstFriv', ['MPFF']),           #08: Hyresinkomster vid frivillig skattskyldighet
    ('InkopVaruAnnatEg', ['VFEU']),         #20: Inköp av varor från annat EU-land
    ('InkopTjanstAnnatEg', ['TFEU']),       #21: Inköp av tjänster från annat EU-land
    ('InkopTjanstUtomEg', ['TFFU']),        #22: Inköp av tjänster från land utanför EU
    ('InkopVaruSverige', ['IVIS']),         #23: Inköp av varor i Sverige
    ('InkopTjanstSverige', ['ITIS']),       #24: Inköp av tjänster i Sverige
    ('MomsUlagImport', ['MBBUI']),          #50: Beskattningsunderlag vid import
    ('ForsVaruAnnatEg', ['VTEU']),          #35: Försäljning av varor till annat EU-land
    ('ForsVaruUtomEg', ['E']),              #36: Försäljning av varor utanför EU
    ('InkopVaruMellan3p', ['3VEU']),        #37: Mellanmans inköp av varor vid trepartshandel
    ('ForsVaruMellan3p', ['3FEU']),         #38: Mellanmans försäljning av varor vid trepartshandel
    ('ForsTjSkskAnnatEg', ['FTEU']),        #39: Försäljning av tjänster när köparen är skattskyldig i annat EU-land
    ('ForsTjOvrUtomEg', ['OTTU']),          #40: Övrig försäljning av tjänster omsatta utom landet
    ('ForsKopareSkskSverige', ['OMSS']),    #41: Försäljning när köparen är skattskyldig i Sverige
    ('ForsOvrigt', ['MF']),                 #42: Övrig försäljning m.m. ???
    ('MomsUtgHog', ['MP1', 'MP1i']),        #10: Utgående moms 25 %
    ('MomsUtgMedel', ['MP2', 'MP2i']),      #11: Utgående moms 12 %
    ('MomsUtgLag', ['MP3', 'MP3i']),        #12: Utgående moms 6 %
    ('MomsInkopUtgHog', ['U1MI']),          #30: Utgående moms 25%
    ('MomsInkopUtgMedel', ['U2MI']),        #31: Utgående moms 12%
    ('MomsInkopUtgLag', ['U3MI']),          #32: Utgående moms 6%
    ('MomsImportUtgHog', ['U1MBBUI']),      #60: Utgående moms 25%
    ('MomsImportUtgMedel', ['U2MBBUI']),    #61: Utgående moms 12%
    ('MomsImportUtgLag', ['U3MBBUI']),      #62: Utgående moms 6%
    ('MomsIngAvdr', ['MomsIngAvdr']),       #48: Ingående moms att dra av
    ('MomsBetala', ['MomsBetala']),         #49: Moms att betala eller få tillbaka
])

class account_vat_declaration(models.Model):
    _name = 'account.vat.declaration'
    _inherit = ['mail.thread']
    
    def _get_tax(self):
        user = self.env.user
        taxes = self.env['account.tax'].search([('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    def _get_year(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    name = fields.Char(default='Moms jan - mars')
    date = fields.Date(help="Planned date")
    state = fields.Selection(selection=[('draft','Draft'),('progress','Progress'),('done','Done'),('canceled','Canceled')],default='draft',track_visibility='onchange')
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Räkenskapsår', help='Håll tom för alla öppna räkenskapsår', default=_get_year)
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True)
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period', required=True)

    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], string='Target Moves')
    free_text = fields.Text(string='Upplysningstext')
    report_file = fields.Binary(string="Report-file")
    eskd_file = fields.Binary(string="eSKD-file")
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat', readonly=True)

    @api.onchange('period_start', 'period_stop', 'target_move')
    def _vat(self):
        if self.period_start and self.period_stop:
            ctx = {
                'period_from': self.period_start.id,
                'period_to': self.period_stop.id,
                'target_move': self.target_move,
            }            
            self.vat_momsingavdr =  sum([self.env.ref('l10n_se_tax_report.%s' % row).with_context(ctx).sum_tax_period() for row in [48]])
            self.vat_momsutg = sum([self.env.ref('l10n_se_tax_report.%s' % row).with_context(ctx).sum_tax_period() for row in [10,11,12,30,31,32,60,61,62]])
            self.vat_momsbetala = self.vat_momsutg + self.vat_momsingavdr
    vat_momsingavdr = fields.Float(string='Vat In', default=0.0, compute="_vat", help='Avläsning av transationer från baskontoplanen.')
    vat_momsutg = fields.Float(string='Vat Out', default=0.0, compute="_vat", help='Avläsning av transationer från baskontoplanen.')
    vat_momsbetala = fields.Float(string='Moms att betala ut (+) eller få tillbaka (-)', default=0.0, compute="_vat", help='Avläsning av skattekonto.')


    @api.one
    def create_eskd(self):
        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id)])
        def parse_xml(recordsets):
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = self.env.user.company_id.company_registry
            moms = etree.SubElement(root, 'Moms')
            period = etree.SubElement(moms, 'Period')
            period.text = self.period_start.date_start[:4] + self.period_start.date_start[5:7]
            for k,v in NAMEMAPPING.items():
                tax = etree.SubElement(moms, k)
                if k == 'ForsMomsEjAnnan':
                    acc = self.env['account.account'].search([('code', 'in', ['3001', '3002', '3003'])])
                    if acc:
                        t = 0
                        for a in acc:
                            t += self._get_account_period_balance(a, self.period_start, self.period_stop, self.target_move)
                        tax.text = str(int(round(abs(t))))
                    else:
                        tax.text = '0'
                elif k == 'MomsBetala':
                    ctx = {
                        'period_from': self.period_start.id,
                        'period_to': self.period_stop.id,
                        'target_move': self.target_move,
                    }
                    tax.text = str(int(round(-(self.env['account.tax'].search([('name', '=', 'MomsUtg')]).with_context(ctx).sum_period + self.env['account.tax'].search([('name', '=', 'MomsIngAvdr')]).with_context(ctx).sum_period))))
                else:
                    acc = self.env['account.tax'].search([('name', 'in', v)])
                    if acc:
                        t = 0
                        for a in acc:
                            t += self.account_sum_period(a, self.period_start.id, self.period_stop.id, self.target_move)
                        tax.text = str(int(round(abs(t))))
                    else:
                        tax.text = '0'
            #~ for record in recordsets:
                #~ tax = etree.SubElement(moms, NAMEMAPPING.get(record.name) or record.name) # TODO: make sure all account.tax name exist here, removed "or" later on
                #~ tax.text = str(int(abs(record.with_context({'period_from': self.period_start.id, 'period_to': self.period_stop.id, 'state': self.target_move}).sum_period)))
            free_text = etree.SubElement(moms, 'TextUpplysningMoms')
            free_text.text = self.free_text or ''
            return root
        xml = etree.tostring(parse_xml(tax_account), pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        self.eskd_file = base64.b64encode(xml)

    def account_sum_period(self, account, period_start, period_stop, target_move):
        return int(abs(account.with_context({'period_from': period_start, 'period_to': period_stop, 'state': target_move}).sum_period))


    def get_all_output_accounts(self):
        accounts = self.env.ref('l10n_se_tax_report.10').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.11').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.12').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.30').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.31').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.32').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.60').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.61').mapped('account_ids')
        accounts |= self.env.ref('l10n_se_tax_report.62').mapped('account_ids')
        return accounts

    def get_all_input_accounts(self):
        accounts = self.env.ref('l10n_se_tax_report.48').mapped('account_ids')
        return accounts

    def get_period_ids(self, period_start, period_stop):
        if period_stop and period_stop.date_start < period_start.date_start:
            raise Warning('Stop period must be after start period')
        if period_stop.date_start == period_start.date_start:
            return [period_start.id]
        else:
            return [r.id for r in self.env['account.period'].search([('date_start', '>=', period_start.date_start), ('date_stop', '<=', period_stop.date_stop), ('special', '=', False)])]

    def _get_account_period_balance(self, account, period_start, period_stop, target_move):
        return sum(account.get_balance(period, target_move) for period in self.env['account.period'].browse(self.get_period_ids(self.period_start, self.period_stop)))

  

    @api.multi
    def create_entry(self):
        kontomoms = self.get_all_output_accounts() | self.get_all_input_accounts()
        moms_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.moms_journal')
        if not moms_journal_id:
            raise Warning('Konfigurera din momsdeklaration journal!')
        else:
            moms_journal = self.env['account.journal'].browse(int(moms_journal_id))
            momsskuld = moms_journal.default_credit_account_id
            momsfordran = moms_journal.default_debit_account_id
            skattekonto = self.env['account.account'].search([('code', '=', '1630')])
            if len(kontomoms) > 0 and momsskuld and momsfordran and skattekonto:
                total = 0.0
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Momsdeklaration',
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
        accounts = self.get_all_output_accounts() | self.get_all_input_accounts()
        tax_accounts = accounts.with_context({'state': self.target_move})
        domain = [('move_id.period_id', 'in', self.get_period_ids(self.period_start, self.period_stop)), ('account_id', 'in', tax_accounts.mapped('id'))]
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
        domain = [('move_id.period_id', 'in', self.get_period_ids(self.period_start, self.period_stop)), ('account_id', 'in', (self.get_all_output_accounts() | self.get_all_input_accounts()).mapped('id'))]
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

    @api.one
    def print_report(self): # make a short cut to print financial report
        afr = self.env['accounting.report'].sudo().create({
            'account_report_id': self.env.ref('l10n_se_tax_report.root').id,
            'target_move': 'all',
            'enable_filter': False,
            'debit_credit': False,
            'date_from_cmp': self.period_start.date_start,
            'date_to_cmp': self.period_stop.date_stop,
        })
        self.report_file = afr.get_pdf()




    # ~ @api.multi
    # ~ def print_report(self):
        # ~ return {
            # ~ 'type': 'ir.actions.act_window',
            # ~ 'res_model': 'accounting.report',
            # ~ 'view_type': 'form',
            # ~ 'view_mode': 'form',
            # ~ 'view_id': self.env.ref('account.accounting_report_view').id,
            # ~ 'target': 'new',
            # ~ 'domain': [],
            # ~ 'context': {
                # ~ 'default_account_report_id': self.env.ref('l10n_se_tax_report.root').id,
                # ~ 'default_date_from': self.period_start.date_start,
                # ~ 'default_date_to': self.period_stop.date_stop,
            # ~ },
        # ~ }

        #~ account_tax_codes = self.env['account.tax'].search([])
        #~ data = {}
        #~ data['ids'] = account_tax_codes.mapped('id')
        #~ data['model'] = 'account.tax'
        #~ return self.env['report'].with_context({'period_ids': self.get_period_ids(self.period_start, self.period_stop), 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_tax_report.moms_report_glabel').name, data=data)
