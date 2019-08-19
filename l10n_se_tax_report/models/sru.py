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
import time
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

# https://www.skatteverket.se/download/18.353fa3f313ec5f91b95111e/1370004596423/SKV269_20_8.pdf
# https://srumaker.se
# https://beta.srumaker.se
# OBS justering: account.financial.report 3.6, tar bort alla konto som tillhör till 3.5. VIKTIGT!!!
# Bokslut verifikat måste ha samma räkenskapsår som deklarationen, Target moves ska vara alla post, bokslutsperiod ska vara ikryssad.


class account_sru_declaration(models.Model):
    _name = 'account.sru.declaration'
    _inherits = {'account.declaration.line.id': 'line_id'}
    _inherit = 'account.declaration'
    _report_name = 'SRU'

    line_id = fields.Many2one('account.declaration.line.id', auto_join=True, index=True, ondelete='cascade', required=True)
    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True, default=_period_start)
    def _period_stop(self):
        return  self.get_next_periods()[1]
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period', required=True, default=_period_stop)
    move_ids = fields.One2many(comodel_name='account.move', inverse_name='sru_declaration_id')
    line_ids = fields.One2many(comodel_name='account.declaration.line', inverse_name='sru_declaration_id')
    @api.one
    def _line_ids(self):
        self.b_line_ids = self.line_ids.filtered(lambda l: l.is_b and not l.is_r)
        self.r_line_ids = self.line_ids.filtered(lambda l: l.is_r and not l.is_b)
    b_line_ids = fields.One2many(comodel_name='account.declaration.line', compute='_line_ids')
    r_line_ids = fields.One2many(comodel_name='account.declaration.line', compute='_line_ids')
    @api.model
    def _search_other_line_ids(self, operator, value):
        return ['&', '&', ('is_b', '=', False), ('is_r', '=', False), ('line_ids', operator, value)] 
    @api.one
    def _compute_other_line_ids(self):
        self.other_line_ids = self.line_ids.filtered(lambda l: not l.is_b and not l.is_r)    
    @api.one
    def _write_other_line_ids(self):
        self.line_ids = self.b_line_ids | self.r_line_ids | self.other_line_ids
    other_line_ids = fields.One2many(comodel_name='account.declaration.line', search='_search_other_line_ids', compute='_compute_other_line_ids', inverse='_write_other_line_ids')
    report_id = fields.Many2one(comodel_name="account.financial.report", required=True)
    arets_intakt = fields.Integer(string='Årets intäkt', readonly=True)
    arets_kostnad = fields.Integer(string='Årets kostnad', readonly=True)
    arets_resultat = fields.Integer(string='Årets resultat', readonly=True)
    tillgangar = fields.Integer(string='Tillgångar', readonly=True)
    eget_kapital_skulder = fields.Integer(string='Eget kapital och skulder', readonly=True)
    fritt_eget_kapital = fields.Integer(string='Fritt eget kapital', readonly=True)
    infosru = fields.Binary(string='INFO.SRU', readonly=True)
    infosru_file_name = fields.Char(string='File Name', default='INFO.SRU')
    datasru = fields.Binary(string='BLANKETTER.SRU', readonly=True)
    datasru_file_name = fields.Char(string='File Name', default='BLANKETTER.SRU')
    upplysningar_1 = fields.Boolean(string='Uppdragstagare (t.ex. redovisningskonsult) har biträtt vid upprättandet av årsredovisningen')
    upplysningar_2 = fields.Boolean(string='Årsredovisningen har varit föremål för revision')

    @api.one
    def _set_date_and_name(self):
            self.accounting_yearend = (self.period_stop == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            d = fields.Date.from_string(self.period_stop.date_stop)
            if d.month >= 1 and d.month <= 4:
                newdate = self.next_monday(datetime(d.year, 11 ,1) )
                self.date = fields.Date.to_string(newdate)
            if d.month >= 5 and d.month <= 6:
                newdate = datetime(d.year, 12, 15)
                self.date = fields.Date.to_string(newdate)
            if d.month >= 7 and d.month <= 8:
                newdate = self.next_monday(datetime(d.year+1, 3 ,1) )
                self.date = fields.Date.to_string(newdate)
            if d.month >= 9 and d.month <= 12:
                newdate = datetime(d.year+1, 7, 1)
                self.date = fields.Date.to_string(newdate)

            # ~ NAME OF SRU FILE
            self.name = '%s %s' % (self._report_name, self.fiscalyear_id.name )

    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear_id(self):
        if self.fiscalyear_id:
            self.period_start = self.fiscalyear_id.period_ids[0]
            self.period_stop  = self.fiscalyear_id.period_ids[-1]
            self._set_date_and_name()

    @api.onchange('period_stop')
    def onchange_period_stop(self):
        if self.period_stop:
            self._set_date_and_name()

    # Skapar bokslut verifikat
    # via vinst:   8999 (D) 2099 (K)
    # via förlust: 2099 (D) 8999 (K)

    @api.one
    def calc_arets_resultat(self):
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_stop.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }
        r_lines = self.line_ids.filtered(lambda l: l.is_r == True)
        r_afr = self.env['account.financial.report'].search([('name', '=', u'RESULTATRÄKNING'), ('parent_id', '=', self.report_id.id)])
        if r_afr:
            arets_intakt_ids = self.env['account.financial.report'].search([('parent_id', 'child_of', r_afr.id), ('sign', '=', 1), ('type', '=', 'accounts')])
            arets_kostnad_ids = self.env['account.financial.report'].search([('parent_id', 'child_of', r_afr.id), ('sign', '=', -1), ('type', '=', 'accounts')])
            arets_intakt = 0
            arets_kostnad = 0
            if len(r_lines) == 0: # do a calculate
                for ai in arets_intakt_ids:
                    arets_intakt += int(abs(sum([a.with_context(ctx).sum_period() for a in ai.account_ids])) or 0.0)
                for ak in arets_kostnad_ids:
                    arets_kostnad += int(abs(sum([a.with_context(ctx).sum_period() for a in ak.account_ids])) or 0.0)
                self.arets_intakt = arets_intakt
                self.arets_kostnad = arets_kostnad
                arets_resultat = self.arets_resultat = arets_intakt - arets_kostnad
                if self.arets_resultat != 0: # if arets_resultat is not 0, update year end entry
                    journal = self.env['account.journal'].search([('code', '=', u'Övr')], limit=1)
                    if journal:
                        entry = self.move_id
                        if not entry:
                            entry = self.env['account.move'].create({
                                'journal_id': journal.id,
                                'period_id': self.period_stop.id,
                                'date': self.period_stop.date_stop,
                                'ref': u'Bokslut',
                            })
                        move_line_list = []
                        arets_resultat_konto_2099 = self.env['account.account'].search([('code', '=', '2099')], limit=1)
                        arets_resultat_konto_8999 = self.env['account.account'].search([('code', '=', '8999')], limit=1)
                        if arets_resultat_konto_2099 and arets_resultat_konto_8999:
                            line_2099 = entry.line_ids.filtered(lambda l: l.account_id.code == '2099')
                            line_8999 = entry.line_ids.filtered(lambda l: l.account_id.code == '8999')
                            if line_2099:
                                line_2099_operator = 1
                                line_2099_id = line_2099[0].id
                            else:
                                line_2099_operator = 0
                                line_2099_id = 0
                            if line_8999:
                                line_8999_operator = 1
                                line_8999_id = line_8999[0].id
                            else:
                                line_8999_operator = 0
                                line_8999_id = 0
                            move_line_list.append((line_8999_operator, line_8999_id, {
                                'name': arets_resultat_konto_8999.name,
                                'account_id': arets_resultat_konto_8999.id,
                                'debit': float(abs(arets_resultat)) if arets_resultat >= 0 else 0.0,
                                'credit': 0.0 if arets_resultat >= 0 else float(abs(arets_resultat)),
                                'move_id': entry.id,
                            }))
                            move_line_list.append((line_2099_operator, line_2099_id, {
                                'name': arets_resultat_konto_2099.name,
                                'account_id': arets_resultat_konto_2099.id,
                                'debit': 0.0 if arets_resultat >= 0 else float(abs(arets_resultat)),
                                'credit': float(abs(arets_resultat)) if arets_resultat >= 0 else 0.0,
                                'move_id': entry.id,
                            }))
                            entry.write({
                                'line_ids': move_line_list,
                            })
                            self.write({'move_id': entry.id})
            else: # read value from lines
                sum_arets_intakt = sum_arets_kostnad = 0
                for li in r_lines.with_context(r_afr=r_afr).filtered(lambda l: l.afr_id.parent_id == l._context.get('r_afr') and l.afr_id.sru not in ['3.24', '3.26', '3.27']):
                    if li.afr_id.sign == 1:
                        sum_arets_intakt += li.balance
                    if li.afr_id.sign == -1:
                        sum_arets_kostnad += li.balance
                self.arets_resultat = sum_arets_intakt - sum_arets_kostnad

    # Uppdaterar bokslut verifikat, skillnad mellan tillgångar och skulder
    # positiv eget kapital: 8899 (D) 2090 (K)
    # negativ eget kapital: 2090 (D) 8899 (K)

    @api.one
    def calc_fritt_eget_kapital(self):
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_stop.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }
        b_lines = self.line_ids.filtered(lambda l: l.is_b == True)
        b_afr = self.env['account.financial.report'].search([('name', '=', u'BALANSRÄKNING'), ('parent_id', '=', self.report_id.id)])
        if b_afr:
            if len(b_lines) == 0: # do a calculate
                def calc_kapital():
                    tillgangar = self.env['account.financial.report'].search([('name', '=', u'Tillgångar'), ('parent_id', '=', b_afr.id)])
                    if tillgangar:
                        tillgangar_children = self.env['account.financial.report'].search([('parent_id', 'child_of', tillgangar.id), ('type', '=', 'accounts')])
                        sum_tillgangar = 0
                        for line in tillgangar_children:
                            sum_tillgangar += int(abs(sum([a.with_context(ctx).sum_period() for a in line.account_ids])) or 0.0)
                        self.tillgangar = sum_tillgangar
                    else:
                        self.tillgangar = 0
                    eget_kapital_skulder = self.env['account.financial.report'].search([('name', '=', u'Eget kapital och skulder')])
                    if eget_kapital_skulder:
                        eget_kapital_skulder_children = self.env['account.financial.report'].search([('parent_id', 'child_of', eget_kapital_skulder.id), ('type', '=', 'accounts')])
                        sum_eget_kapital_skulder = 0
                        for line in eget_kapital_skulder_children:
                            sum_eget_kapital_skulder += int(abs(sum([a.with_context(ctx).sum_period() for a in line.account_ids])) or 0.0)
                        self.eget_kapital_skulder = sum_eget_kapital_skulder
                    else:
                        self.eget_kapital_skulder = 0
                    return self.tillgangar - self.eget_kapital_skulder
                fritt_eget_kapital = calc_kapital() # get difference
                if fritt_eget_kapital != 0: # if fritt_eget_kapital is not 0, update year end entry
                    journal = self.env['account.journal'].search([('code', '=', u'Övr')], limit=1)
                    if journal:
                        entry = self.move_id
                        if not entry:
                            entry = self.env['account.move'].create({
                                'journal_id': journal.id,
                                'period_id': self.period_stop.id,
                                'date': self.period_stop.date_stop,
                                'ref': u'Bokslut',
                            })
                        move_line_list = []
                        arets_resultat_konto_2090 = self.env['account.account'].search([('code', '=', '2090')], limit=1)
                        arets_resultat_konto_8899 = self.env['account.account'].search([('code', '=', '8899')], limit=1)
                        if arets_resultat_konto_2090 and arets_resultat_konto_8899:
                            line_2090 = entry.line_ids.filtered(lambda l: l.account_id.code == '2090')
                            line_8899 = entry.line_ids.filtered(lambda l: l.account_id.code == '8899')
                            if line_2090:
                                line_2090_operator = 1
                                line_2090_id = line_2090[0].id
                            else:
                                line_2090_operator = 0
                                line_2090_id = 0
                            if line_8899:
                                line_8899_operator = 1
                                line_8899_id = line_8899[0].id
                            else:
                                line_8899_operator = 0
                                line_8899_id = 0
                            move_line_list.append((line_8899_operator, line_8899_id, {
                                'name': arets_resultat_konto_8899.name,
                                'account_id': arets_resultat_konto_8899.id,
                                'debit': float(abs(fritt_eget_kapital)) if fritt_eget_kapital >= 0 else 0.0,
                                'credit': 0.0 if fritt_eget_kapital >= 0 else float(abs(fritt_eget_kapital)),
                                'move_id': entry.id,
                            }))
                            move_line_list.append((line_2090_operator, line_2090_id, {
                                'name': arets_resultat_konto_2090.name,
                                'account_id': arets_resultat_konto_2090.id,
                                'debit': 0.0 if fritt_eget_kapital >= 0 else float(abs(fritt_eget_kapital)),
                                'credit': float(abs(fritt_eget_kapital)) if fritt_eget_kapital >= 0 else 0.0,
                                'move_id': entry.id,
                            }))
                            entry.write({
                                'line_ids': move_line_list,
                            })
                            self.write({'move_id': entry.id})
                self.fritt_eget_kapital = calc_kapital() # redo calculate so it will be balanced
            else: # read value from lines
                sum_tillgangar = sum_eget_kapital_skulder = 0
                for li in b_lines.with_context(b_afr=b_afr).filtered(lambda l: l.afr_id.parent_id == l._context.get('b_afr')):
                    if li.afr_id.sign == 1:
                        sum_tillgangar += li.balance
                    if li.afr_id.sign == -1:
                        sum_eget_kapital_skulder += li.balance
                self.fritt_eget_kapital = sum_tillgangar - sum_eget_kapital_skulder


    @api.one
    def do_draft(self):
        super(account_sru_declaration, self).do_draft()
        for move in self.move_ids:
            move.sru_declaration_id = None

    @api.one
    def do_cancel(self):
        super(account_sru_declaration, self).do_draft()
        for move in self.move_ids:
            move.sru_declaration_id = None

    @api.one
    def calculate(self):
        if self.state not in ['draft']:
            raise Warning("Du kan inte beräkna i denna status, ändra till utkast")
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

        sru_lines = self.env['account.declaration.line'].search([('sru_declaration_id', '=', self.id)])
        sru_lines.unlink()
        b_afr = self.env['account.financial.report'].search([('name', '=', u'BALANSRÄKNING'), ('parent_id', '=', self.report_id.id)])
        r_afr = self.env['account.financial.report'].search([('name', '=', u'RESULTATRÄKNING'), ('parent_id', '=', self.report_id.id)])
        
        period_ids = self.env['account.period'].get_period_ids(self.period_start,self.period_stop)
        grouped_lines = self.env['account.move.line'].read_group([('move_id.period_id','in',period_ids)],['balance','account_id'],['account_id'])
        # ~ accounts = {'%s' % g['account_id']: g['balance'] for g in grouped_lines}
        move_line_ids = line.with_context(ctx).get_moveline_ids()
        raise Warning(move_line_ids)

        def create_lines(afr, dec, is_b=False, is_r=False):
            lines = self.env['account.financial.report'].search([('parent_id', 'child_of', afr.id), ('type', '=', 'accounts')])
            for line in lines:
                
                period_ids = self.env['account.period'].get_period_ids(self.period_start,self.period_stop)
                _logger.debug('SRU line %s %s' % (line.name,'pelle'))

                balance = sum(self.env['account.move.line'].read(move_line_ids,{'balance'}))
                # ~ balance = sum([a.with_context(ctx).sum_period() for a in self.env['account.financial.report'].search([('parent_id', 'child_of', line.id), ('type', '=', 'accounts')]).mapped('account_ids')])
                _logger.debug('SRU line %s %s' % (line.name,balance))
                sru_line = self.env['account.declaration.line'].create({
                    'sru_declaration_id': dec.id,
                    'afr_id': line.id,
                    'balance': int(abs(balance)),
                    'sign': 1 if balance >= 0.0 else -1,
                    'name': line.name,
                    'level': line.level,
                    'move_line_ids': [(6, 0, move_line_ids)],
                    'is_b': is_b,
                    'is_r': is_r,
                })
                # take care of 3.26 and 3.27
                if line.sru == '3.26': # vinst rad
                    if sru_line.sign == -1: # är förlust, vinst rad ska vara 0
                        sru_line.balance = 0
                if line.sru == '3.27': # förlust rad
                    if sru_line.sign == 1: # är vinst, förlust rad ska vara 0
                        sru_line.balance = 0
        if b_afr:
            create_lines(b_afr, self, is_b=True)
        if r_afr:
            create_lines(r_afr, self, is_r=True)

        # encoding="ISO-8859-1"
        self.infosru = base64.b64encode(self._parse_infosru(self))
        self.datasru = base64.b64encode(self._parse_datasru(self))
        if self.state in ['draft']:
            self.state = 'done'

    # Create INFO.SRU
    def _parse_infosru(self, declaration):
        data = u'''#DATABESKRIVNING_START
#PRODUKT SRU
#SKAPAD {create_datetime}
#PROGRAM Odoo 10.0
#FILNAMN BLANKETTER.SRU
#DATABESKRIVNING_SLUT
#MEDIELEV_START
#ORGNR 16{org_number}
#NAMN {company_name}
#ADRESS {company_address}
#POSTNR {company_zip}
#POSTORT {company_city}
#EMAIL {company_email}
#TELEFON {company_phone}
#MEDIELEV_SLUT'''.format(
    create_datetime = fields.Datetime.now().replace('-', '').replace(':', ''),
    org_number = self.env.user.company_id.company_registry.replace('-', ''),
    company_name = self.env.user.company_id.name,
    company_address = self.env.user.company_id.street or self.env.user.company_id.street2,
    company_zip = self.env.user.company_id.zip or '',
    company_city = self.env.user.company_id.city or '',
    company_email = self.env.user.company_id.email or '',
    company_phone = self.env.user.company_id.phone or ''
)
        return data

    # Create BLANKETTER.SRU
    @api.model
    def _parse_datasru(self, declaration): # 2: K2 företag, R: kolumn 2.1 - 3.27, P4: bokslut period kvartal 4
        def get_uppgift(declaration_line_ids):
            u = []
            for l in declaration_line_ids:
                if l.balance:
                    if l.sign == 1:
                        u.append('#UPPGIFT %s %s' %(l.afr_id.field_code, l.balance))
                    else:
                        if l.afr_id.field_code_neg:
                            u.append('#UPPGIFT %s %s' %(l.afr_id.field_code_neg, l.balance))
                        else:
                            u.append('#UPPGIFT %s %s' %(l.afr_id.field_code, l.balance))
            return '\n'.join(u)

        def get_skott(declaration_line_ids):
            skott = 0
            for l in declaration_line_ids:
                if l.balance:
                    if l.afr_id.sign == 1:
                        skott += l.balance
                    else:
                        skott -= l.balance
            if skott > 0:
                return '#UPPGIFT 7670 %s' %skott
            if skott < 0:
                return '#UPPGIFT 7770 %s' %skott
            else:
                return ''

        def get_ink2r_blankett():
            blankett = u'''#BLANKETT INK2R-{year}P4
#IDENTITET 16{org_number} {create_datetime}
#NAMN {company_name}
{uppgift}
#SYSTEMINFO Odoo 10.0
#BLANKETTSLUT'''.format(
    year = declaration.fiscalyear_id.code,
    org_number = self.env.user.company_id.company_registry.replace('-', ''),
    create_datetime = fields.Datetime.now().replace('-', '').replace(':', ''),
    company_name = self.env.user.company_id.name,
    uppgift = get_uppgift(declaration.b_line_ids | declaration.r_line_ids)
)
            return blankett

        def get_ink2s_blankett():
            uppgift = get_uppgift(declaration.other_line_ids)
            skott = get_skott(declaration.other_line_ids)
            if len(uppgift) > 0:
                blankett = u'''#BLANKETT INK2S-{year}P4
#IDENTITET 16{org_number} {create_datetime}
#NAMN {company_name}
{uppgift}
{skott}
{upplysningar_1}
{upplysningar_2}
#SYSTEMINFO Odoo 10.0
#BLANKETTSLUT'''.format(
    year = declaration.fiscalyear_id.code,
    org_number = self.env.user.company_id.company_registry.replace('-', ''),
    create_datetime = fields.Datetime.now().replace('-', '').replace(':', ''),
    company_name = self.env.user.company_id.name,
    uppgift = uppgift,
    skott = skott,
    upplysningar_1 = '#UPPGIFT 8040 X' if self.upplysningar_1 else '#UPPGIFT 8041 X',
    upplysningar_2 = '#UPPGIFT 8044 X' if self.upplysningar_2 else '#UPPGIFT 8045 X'
)
                return '\n%s' % blankett
            else:
                return ''

        data = u'''{ink2r_blankett}{ink2s_blankett}
#FIL_SLUT'''.format(
    ink2r_blankett = get_ink2r_blankett(),
    ink2s_blankett = get_ink2s_blankett()
)
        return data

    @api.one
    def regenerate_sru_files(self):
        if self.b_line_ids and self.r_line_ids:
            self.infosru = base64.b64encode(self._parse_infosru(self))
            self.datasru = base64.b64encode(self._parse_datasru(self))

    @api.model
    def get_next_periods(self):
        last_declaration = self.search([], order='date_stop desc', limit=1)
        if not last_declaration:
            last_year = str(int(fields.Date.today()[:4]) - 1)
            fiscalyear = self.env['account.fiscalyear'].search([('code', '=', last_year)])
            if not fiscalyear:
                raise Warning(_('Please add fiscal year for %s') %last_year)
            start_period = self.env['account.period'].search([('fiscalyear_id', '=', fiscalyear.id), ('date_start', '=', '%s-01-01' %last_year), ('date_stop', '=', '%s-01-31' %last_year), ('special', '=', False)])
            stop_period = self.env['account.period'].search([('fiscalyear_id', '=', fiscalyear.id), ('date_start', '=', '%s-12-01' %last_year), ('date_stop', '=', '%s-12-31' %last_year)])
            return [start_period, stop_period]
        else:
            next_year = str(int(last_declaration.period_stop.date_start[:4]) + 1)
            fiscalyear = self.env['account.fiscalyear'].search([('code', '=', next_year)])
            if not fiscalyear:
                raise Warning(_('Please add fiscal year for %s') %next_year)
            start_period = self.env['account.period'].search([('fiscalyear_id', '=', fiscalyear.id), ('date_start', '=', '%s-01-01' %next_year), ('date_stop', '=', '%s-01-31' %next_year), ('special', '=', False)])
            stop_period = self.env['account.period'].search([('fiscalyear_id', '=', fiscalyear.id), ('date_start', '=', '%s-12-01' %next_year), ('date_stop', '=', '%s-12-31' %next_year)])
            return [start_period, stop_period]

    # not in use
    @api.multi
    def report_resultatrakning_structure(self):
        structure = [
            {
                u'Rörelseintäkter, lagerförändringar m.m.': {
                    u'Summa rörelseintäkter, lagerförändringar m.m.': ['3.1', '3.2', '3.3', '3.4']
                }
            },
            {
                u'Rörelsekostnader': {
                    u'Summa rörelsekostnader': ['3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14']
                }
            },
            {
                u'Rörelseresultat': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14']
            },
            {
                u'Finansiella poster': {
                    u'Summa finansiella poster': ['3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22']
                }
            },
            {
                u'Resultat efter finansiella poster': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22']
            },
            {
                u'Bokslutsdispositioner': {
                    u'Summa finansiella poster': ['3.23', '3.24']
                }
            },
            {
                u'Resultat före skatt': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22', '3.23', '3.24']
            },
            {
                u'Skatter': {
                    u'Skatt på årets resultat': ['3.25']
                }
            },
            {
                u'Årets resultat': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22', '3.23', '3.24', '3.25']
            },
        ]
        self.ensure_one()
        result = []
        for s in structure:
            if isinstance(s.items()[0][1], dict):
                result.append({
                    'name': s.items()[0][0],
                    'value': self.env['account.declaration.line'].browse()
                })
                result.append({
                    'name': s.items()[0][1].items()[0][0],
                    'value': self.r_line_ids.with_context(sru_codes=s.items()[0][1].items()[0][1]).filtered(lambda l: l.afr_id.sru in l._context.get('sru_codes') and l.balance != 0)
                })
            if isinstance(s.items()[0][1], list):
                result.append({
                    'name': s.items()[0][0],
                    'value': self.r_line_ids.with_context(sru_codes=s.items()[0][1]).filtered(lambda l: l.afr_id.sru in l._context.get('sru_codes') and l.balance != 0)
                })
        return result

    @api.multi
    def report_resultatrakning(self, name):
        srus = {
            'rorelseintakter_lagerforandringar_m_m': ['3.1', '3.2', '3.3', '3.4'],
            'rorelsekostnader': ['3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14'],
            'rorelseresultat': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14'],
            'finansiella_poster': ['3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22'],
            'resultat_efter_finansiella_poster': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22'],
            'bokslutsdispositioner': ['3.23', '3.24'],
            'resultat_fore_skatt': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22', '3.23', '3.24'],
            'skatt_pa_arets_resultat': ['3.25'],
            'arets_resultat': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16', '3.17', '3.18', '3.19', '3.20', '3.21', '3.22', '3.23', '3.24', '3.25']
        }
        return self.report_result_value(srus[name])

    @api.multi
    def report_result_value(self, sru_codes):
        self.ensure_one()
        return self.r_line_ids.with_context(sru_codes=sru_codes).filtered(lambda l: l.afr_id.sru in l._context.get('sru_codes') and l.balance != 0)

    @api.multi
    def report_sum_resultatrakning(self, name):
        self.ensure_one()
        s = sum([line.balance * (1 if line.afr_id.sign == 1 else -1) for line in self.report_resultatrakning(name)])
        return s if s != 0 else ''

    @api.model
    def find_balansrakning(self, name):
        financial_report_lst = {
            u'anlaggningstillgangar': self.env['account.financial.report'].search([('name', '=', u'Anläggningstillgångar')]),
            u'omsattningstillgangar': self.env['account.financial.report'].search([('name', '=', u'Omsättningstillgångar')]),
            u'eget_kapital': self.env['account.financial.report'].search([('name', '=', u'Eget kapital')]),
            u'obeskattade_reserver': self.env['account.financial.report'].search([('name', '=', u'Obeskattade reserver')]),
            u'avsattningar': self.env['account.financial.report'].search([('name', '=', u'Avsättningar')]),
            u'langfristiga_skulder': self.env['account.financial.report'].search([('name', '=', u'Långfristiga skulder (förfaller senare än 12 månader från balansdagen)')]),
            u'kortfristiga_skulder': self.env['account.financial.report'].search([('name', '=', u'Kortfristiga skulder (förfaller inom 12 månader från balansdagen)')]),
            u'eget_kapital_och_skulder': self.env['account.financial.report'].search([('name', '=', u'Eget kapital och skulder')])
        }
        return financial_report_lst.get(name)

    @api.multi
    def report_balansrakning(self, name):
        parent_afr = self.find_balansrakning(name)
        if parent_afr:
            fr_children = self.env['account.financial.report'].search([('id', 'child_of', parent_afr.id)])
            res = []
            for b_line in self.b_line_ids.with_context(fr_children=fr_children).filtered(lambda b: b.balance != 0 and b.afr_id in b._context.get('fr_children')):
                res.append(b_line)
            return res

    @api.multi
    def report_sum_balansrakning(self, name):
        self.ensure_one()
        parent_afr = self.find_balansrakning(name)
        if parent_afr:
            children_afr_lines = self.env['account.financial.report'].search([('id', 'child_of', parent_afr.id)])
            lines = self.b_line_ids.with_context(children_afr_lines=children_afr_lines).filtered(lambda l: l.afr_id in l._context.get('children_afr_lines') and l.balance != 0)
            s = sum([line.balance * (1 if line.afr_id.sign == 1 else -1) for line in lines])
            return s if s != 0 else ''


class account_move(models.Model):
    _inherit = 'account.move'

    sru_declaration_id = fields.Many2one(comodel_name='account.agd.declaration')


class account_declaration_line(models.Model):
    _inherit = 'account.declaration.line'

    is_b = fields.Boolean(string='Är Balansräkning')
    is_r = fields.Boolean(string='Är Resultaträkning')
    sru_declaration_id = fields.Many2one(comodel_name='account.sru.declaration')
    afr_id = fields.Many2one(comodel_name='account.financial.report', string='Finansiella rapporter ID')
    sign = fields.Selection([(1, '+'), (-1, '-')], string='Sign', default=1, help='Visar balans resultat positiv eller negativ, är INTE samma sign som på finansiella rapport.')

    @api.onchange('afr_id')
    def afr_onchange(self):
        self.name = self.afr_id.name

    @api.multi
    def report_adl_get_balance(self):
        return self.balance * (1 if self.afr_id.sign == 1 else -1)
