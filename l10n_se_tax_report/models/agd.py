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


# order must be correct
TAGS = [
    'LonBrutto',        #50: Avgiftspliktig bruttolön utom förmåner
    'Forman',           #51: Avgiftspliktiga förmåner
    'AvdrKostn',        #52: Avdrag för utgifter
    'SumUlagAvg',       #53: Sammanlagt underlag för arbetsgivaravgifter och särskild löneskatt
    'UlagAvgHel',       #55:  san  Full arbetsgivaravgift för födda 1953 eller senare (55 = 53 - 57 - 59 - 61 - 65 - 69)
    'AvgHel',           #56: (san) 31,42% av #55
    'UlagAvgAldersp',   #59:  sap  Arbetsgivaravgift för 66-80 år
    'AvgAldersp',       #60: (sap) 16,36% av #59
    'UlagAlderspSkLon', #57??
    'AvgAlderspSkLon',  #58??
    'UlagSkLonSarsk',   #61:  sapx Särskild löneskatt för 81 år eller äldre
    'SkLonSarsk',       #62: (sapx)6,15% av #61
    'UlagAvgAmbassad',  #65: Ambassader och företag utan fast driftställe i Sverige samt särskild löneskatt på vissa försäkringar m.m.
    'AvgAmbassad',      #66: Se uträkningsruta
    # ~ 'KodAmerika',       #67: Kod USA, Kanada, Québec m.fl.
    'UlagAvgAmerika',   #69:
    'AvgAmerika',       #70: Se uträkningsruta
    'UlagStodForetag',  #73: Forskning och utveckling
    'AvdrStodForetag',  #74: Avdrag 10%, dock högst 230000 kr
    'UlagStodUtvidgat', #75: Regionalt stöd för vissa branscher i stödområde
    'AvdrStodUtvidgat', #76: Avdrag 10%, dock högst 7100 kr
    'SumAvgBetala',     #78: Summa arbetsgivaravgifter
    'UlagSkAvdrLon',    #81: Lön och förmåner inkl. SINK
    'SkAvdrLon',        #82: Från lön och förmåner
    'UlagSkAvdrPension',#83: Pension, livränta, försäkringsersättning inkl. SINK
    'SkAvdrPension',    #84: Från pension m.m.
    'UlagSkAvdrRanta',  #85: Ränta och utdelning
    'SkAvdrRanta',      #86: Från ränta och utdelning
    'UlagSumSkAvdr',    #87: Summa underlag för skatteanvdrag
    'SumSkAvdr',        #88: Summa avdragen skatt
    'SjukLonKostnEhs'   #99: Summa arbetsgivaravgifter och avdragen skatt att betala
]

class account_agd_declaration(models.Model):
    _name = 'account.agd.declaration'
    _inherit = 'account.vat.declaration'


    date_stop = fields.Date(related='period_stop.date_start',store=True)
    @api.onchange('period_start')
    def onchange_period_start(self):
        if self.period_start:
            # ~ self.accounting_yearend = (self.period_start == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            self.date = fields.Date.to_string(fields.Date.from_string(self.period_start.date_stop) + timedelta(days=12))
            self.name = 'Agd %s' % (self.env['account.period'].period2month(self.period_start,short=False)))

    @api.onchange('period_start','target_move','accounting_method','accounting_yearend')
    def _vat(self):
        pass
        
        if self.period_start and self.period_stop:
            ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
            self.SumSkAvdr = round(sum([self.env.ref('l10n_se_tax_report.agd_report_%s' % row).with_context(ctx).sum_tax_period() for row in [48]])) * -1.0
            self.SumAvgBetala = round(sum([tax.with_context(ctx).sum_period for row in [10,11,12,30,31,32,60,61,62] for tax in self.env.ref('l10n_se_tax_report.%s' % row).mapped('tax_ids')])) * -1.0
            self.ag_betala = self.vat_momsutg + self.vat_momsingavdr

    SumSkAvdr    = fields.Float(compute='_vat')
    SumAvgBetala = fields.Float(compute='_vat')
    ag_betala  = fields.Float(compute='_vat')
    
    baskonto = fields.Float(string='Baskonto', default=0.0, readonly=True, help='Avläsning av transationer från baskontoplanen.')
    agavgpres = fields.Float(string='Arbetsgivaravgift & Preliminär skatt', default=0.0, readonly=True)
    
    @api.multi
    def show_agavgpres(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in',self.env.ref('l10n_se_tax_report.48').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action


    @api.one
    def calculate(self): # make a short cut to print financial report
        if self.state not in ['draft']:
            raise Warning("Du kan inte beräkna i denna status, ändra till utkast")
        if self.state in ['draft']:
            self.state = 'done'
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_stop.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }

        ##
        ####  Create report lines
        ##

        for row in TAGS:
            line = self.env.ref('l10n_se_tax_report.agd_report_%s' % row)
            self.env['account.vat.declaration.line'].create({
                'declaration_id': self.id,
                'balance': (line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign or 0.0,
                'name': line.name,
                'level': line.level,
                'move_line_ids': [(6,0,line.with_context(ctx).get_moveline_ids())],
                })

        ##
        #### Mark Used moves
        ##

        for move in self.line_ids.mapped('move_line_ids').mapped('move_id'):
            move.vat_declaration_id = self.id

        ##
        #### Create eSDK-file
        ##

        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('account.tax_group_taxes').id)])
        def parse_xml(recordsets,ctx):
            root = etree.Element('eSKDUpload', Version="6.0")
            orgnr = etree.SubElement(root, 'OrgNr')
            orgnr.text = self.env.user.company_id.company_registry or ''
            moms = etree.SubElement(root, 'Moms')
            period = etree.SubElement(moms, 'Period')
            period.text = self.period_start.date_start[:4] + self.period_start.date_start[5:7]
            for row in TAGS.items():
                line = self.env.ref('l10n_se_tax_report.agd_report_%s' % row)
                amount = str(int(abs(round(line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign) or 0))
                if not amount == '0':
                    tax = etree.SubElement(moms, row)
                    tax.text = amount
            momsbetala = etree.SubElement(moms, 'MomsBetala')
            momsbetala.text = str(int(round(self.vat_momsbetala)))
            free_text = etree.SubElement(moms, 'TextUpplysningMoms')
            free_text.text = self.free_text or ''
            return root
        xml = etree.tostring(parse_xml(tax_account,ctx), pretty_print=True, encoding="ISO-8859-1")
        xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        self.eskd_file = base64.b64encode(xml)

        ##
        #### Create move
        ##

        #TODO check all warnings

        moms_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.moms_journal')
        if not moms_journal_id:
            raise Warning('Konfigurera din momsdeklaration journal!')
        else:
            moms_journal = self.env['account.journal'].browse(int(moms_journal_id))
            momsskuld = moms_journal.default_credit_account_id
            momsfordran = moms_journal.default_debit_account_id
            skattekonto = self.env['account.account'].search([('code', '=', '1630')])
            if momsskuld and momsfordran and skattekonto:
                entry = self.env['account.move'].create({
                    'journal_id': moms_journal.id,
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Momsdeklaration',
                })
                if entry:
                    move_line_list = []
                    moms_diff = 0.0
                    for k in self.env.ref('l10n_se_tax_report.48').mapped('account_ids'): # kollar på 2640 konton, ingående moms
                        credit = k.with_context(ctx).sum_period()
                        move_line_list.append((0, 0, {
                            'name': k.name,
                            'account_id': k.id,
                            'credit': credit,
                            'debit': 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff -= credit
                    for k in set([a for row in [10,11,12,30,31,32,60,61,62] for a in self.env.ref('l10n_se_tax_report.%s' % row).mapped('account_ids')]): # kollar på 26xx konton, utgående moms
                        debit = abs(k.with_context(ctx).sum_period())
                        move_line_list.append((0, 0, {
                            'name': k.name,
                            'account_id': k.id,
                            'debit': debit,
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        moms_diff += debit
                    if self.vat_momsbetala < 0.0: # momsfordran, moms ska få tillbaka
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id, # moms_journal.default_debit_account_id
                            'partner_id': '',
                            'debit': abs(self.vat_momsbetala),
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsfordran.name,
                            'account_id': momsfordran.id,
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': abs(self.vat_momsbetala),
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': abs(self.vat_momsbetala),
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                    if self.vat_momsbetala > 0.0: # moms redovisning, moms ska betalas in
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id, # moms_journal.default_credit_account_id
                            'partner_id': '',
                            'debit': 0.0,
                            'credit': self.vat_momsbetala,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': momsskuld.name,
                            'account_id': momsskuld.id,
                            'partner_id': '',
                            'debit': self.vat_momsbetala,
                            'credit': 0.0,
                            'move_id': entry.id,
                        }))
                        move_line_list.append((0, 0, {
                            'name': skattekonto.name,
                            'account_id': skattekonto.id,
                            'partner_id': self.env.ref('base.res_partner-SKV').id,
                            'debit': 0.0,
                            'credit': self.vat_momsbetala,
                            'move_id': entry.id,
                        }))
                    if abs(moms_diff) - abs(self.vat_momsbetala) != 0.0:
                        oresavrundning = self.env['account.account'].search([('code', '=', '3740')])
                        oresavrundning_amount = abs(abs(moms_diff) - abs(self.vat_momsbetala))
                        move_line_list.append((0, 0, {
                            'name': oresavrundning.name,
                            'account_id': oresavrundning.id,
                            'partner_id': '',
                            'debit': oresavrundning_amount if moms_diff < self.vat_momsbetala else 0.0,
                            'credit': oresavrundning_amount if moms_diff > self.vat_momsbetala else 0.0,
                            'move_id': entry.id,
                        }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id})
            else:
                raise Warning(_('Kontomoms: %sst, momsskuld: %s, momsfordran: %s, skattekonto: %s') %(len(kontomoms), momsskuld, momsfordran, skattekonto))

    
-------------

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
            'report_file': '/web/content/agd.declaration/%s/eskd_file/%s?download=true' %(self.id, 'ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]))
            #for v7.0, v8.0
            #'report_file': '/web/binary/saveas?model=agd.declaration&field=eskd_file&filename_field=%s&id=%s' %('ag-%s.txt' %(self.period.date_start[:4] + self.period.date_start[5:7]), self.id)
        }

    @api.onchange('period', 'target_move')
    def read_account(self):
        if self.period:
            tax_account = self.env['account.tax'].with_context({'period_id': self.period.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
            if tax_account:
                sum_baskonto = 0.0
                for account in self.env['account.financial.report'].search([('tax_ids', 'in', tax_account.mapped('children_tax_ids').mapped('id'))]).mapped('account_ids'):
                    sum_baskonto += account.get_balance(self.period, self.target_move)
                self.baskonto = -sum_baskonto
                self.agavgpres = -tax_account.sum_period

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

    def print_report(self): # make a short cut to print financial report
        afr = self.env['accounting.report'].sudo().create({
            'account_report_id': self.env.ref('l10n_se_tax_report.agd_report').id,
            'target_move': 'all',
            'enable_filter': False,
            'debit_credit': False,
            'date_from_cmp': self.period.date_start,
            'date_to_cmp': self.period.date_stop,
        })
        return afr.check_report()

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
                # ~ 'default_account_report_id': self.env.ref('l10n_se_tax_report.agd_report').id,
                # ~ 'default_date_from': self.period.date_start,
                # ~ 'default_date_to': self.period.date_stop,
            # ~ },
        # ~ }

        #~ account_tax_codes = self.env['account.tax'].search([])
        #~ data = {}
        #~ data['ids'] = account_tax_codes.mapped('id')
        #~ data['model'] = 'account.tax'
        #~ return self.env['report'].with_context({'period_id': self.period.id, 'state': self.target_move}).get_action(account_tax_codes, self.env.ref('l10n_se_tax_report.ag_report_glabel').name, data=data)
