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
import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

# Momsredovisning enligt bokslutsmetoden (kontantmetoden) respektive fakturametoden
# Vid kontantmetoden skall 15xx kredit (betalda kundfordringar) redovisas som ingående moms
# och 264x debet (betalda leverantörsfordringar) redovisas som utgående moms
#
# Period   A-id konto   benämning           debet   kredit     tax
# 1803      A01 1510   kundfordran          6250
# 1803          2610   Utgående moms 25%            1250       MP1/MP1i
# 1803          3001   gem                          5000
#
# 1803      A02 2440   Leverantörsskuld             12500
# 1803          2640   Ing moms             2500               I/Ii
# 1803          5410   Förbrukningsinv      10000
#
# 1804      A01 1510   Kundfordran                  6250
# 1804          1931   Bankgiro             6250
#
# 1804          1930   Bankgiro                     12500
# 1804      A02 2440   Leverantörsskuld     12500
#
# 1805          1930   Bank                         25000
# 1805          2640   Ing moms             5000               I/Ii
# 1805          5410   Förbrukningsinv      20000
#
# 1806      A03 1510   kundfordran          50000
# 1806          2611   Utgående moms 25%            10000       MP1/MP1i
# 1806          3041   försäljning                  40000
#
# 1807          1930   Bankgiro             50000
# 1807      A03 1510   Kundfordran                  50000
#
# Momsrapport för 1804 - 1806 skall redovisa Utg/ing 2500 från 1803 (kontantmetoden)
# Alla 19x account.line 1804/06 -> account.move -> A-id -> account.line -> account.tax
# Alla 19x account.move.line med tax_line_id
#
# Fakturametoden
# Alla account.move 1804/06 -> account.line -> account.tax
#

# Typ               Period      Slutperiod  Ingående    Utgående
# Fakturametoden    p04 - p06               5000        10000
# Kontantmetoden    p04 - p06               7500        1250
# Kontantmetoden    p04 - p06   Ja          7500        11250

# order must be correct
NAMEMAPPING = OrderedDict([
    ('ForsMomsEjAnnan', 5),          #05: Momspliktig försäljning som inte ingår i annan ruta nedan
    ('UttagMoms', 6),                #06: Momspliktiga uttag
    ('UlagMargbesk', 7),             #07: Beskattningsunderlag vid vinstmarginalbeskattning
    ('HyrinkomstFriv', 8),           #08: Hyresinkomster vid frivillig skattskyldighet
    ('InkopVaruAnnatEg', 20),        #20: Inköp av varor från annat EU-land
    ('InkopTjanstAnnatEg', 21),      #21: Inköp av tjänster från annat EU-land
    ('InkopTjanstUtomEg', 22),       #22: Inköp av tjänster från land utanför EU
    ('InkopVaruSverige', 23),        #23: Inköp av varor i Sverige
    ('InkopTjanstSverige', 24),      #24: Inköp av tjänster i Sverige
    ('MomsUlagImport', 50),          #50: Beskattningsunderlag vid import
    ('ForsVaruAnnatEg', 35),         #35: Försäljning av varor till annat EU-land
    ('ForsVaruUtomEg', 36),          #36: Försäljning av varor utanför EU
    ('InkopVaruMellan3p', 37),       #37: Mellanmans inköp av varor vid trepartshandel
    ('ForsVaruMellan3p', 38),        #38: Mellanmans försäljning av varor vid trepartshandel
    ('ForsTjSkskAnnatEg', 39),       #39: Försäljning av tjänster när köparen är skattskyldig i annat EU-land
    ('ForsTjOvrUtomEg', 40),         #40: Övrig försäljning av tjänster omsatta utom landet
    ('ForsKopareSkskSverige', 41),   #41: Försäljning när köparen är skattskyldig i Sverige
    ('ForsOvrigt', 42),              #42: Övrig försäljning m.m. ???
    ('MomsUtgHog', 10),              #10: Utgående moms 25 %
    ('MomsUtgMedel', 11),            #11: Utgående moms 12 %
    ('MomsUtgLag', 12),              #12: Utgående moms 6 %
    ('MomsInkopUtgHog', 30),         #30: Utgående moms 25%
    ('MomsInkopUtgMedel', 31),       #31: Utgående moms 12%
    ('MomsInkopUtgLag', 32),         #32: Utgående moms 6%
    ('MomsImportUtgHog', 60),        #60: Utgående moms 25%
    ('MomsImportUtgMedel', 61),      #61: Utgående moms 12%
    ('MomsImportUtgLag', 62),        #62: Utgående moms 6%
    ('MomsIngAvdr', 48),             #48: Ingående moms att dra av
#    ('MomsBetala', 49),             #49: Moms att betala eller få tillbaka | hard coded
])


class account_declaration(models.Model):
    _name = 'account.declaration'
    _inherit = ['mail.thread']
    _report_name = 'Moms'

    name = fields.Char()
    date = fields.Date(help="Planned date, date when to report Skatteverket or do the declaration. Usually monday second week after period, but check calendar at Skatteverket")
    state = fields.Selection(selection=[('draft','Draft'),('done','Done'),('canceled','Canceled')],default='draft',track_visibility='onchange')
    def _fiscalyear_id(self):
        return self.env['account.fiscalyear'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string=u'Räkenskapsår', help='Håll tom för alla öppna räkenskapsår', default=_fiscalyear_id)
    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,default=_period_start)
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period',default=_period_start)
    target_move = fields.Selection(selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')], default='posted',string='Target Moves')
    def _accounting_method(self):
        return  self.env['ir.config_parameter'].get_param(key='l10n_se_tax_report.accounting_method', default='invoice')
    accounting_method = fields.Selection(selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'),], default=_accounting_method,string='Redovisningsmetod',help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden skall välja fakturametoden i sista perioden/bokslutsperioden")
    accounting_yearend = fields.Boolean(string="Bokslutsperiod",help="I bokslutsperioden skall även utestående fordringar ingå i momsredovisningen vid kontantmetoden")
    free_text = fields.Text(string='Upplysningstext')
    report_file = fields.Binary(string="Report-file",readonly=True)
    eskd_file = fields.Binary(string="eSKD-file",readonly=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat', readonly=True)
    date_stop = fields.Date(related='period_start.date_stop',store=True)
    event_id = fields.Many2one(comodel_name='calendar.event',readonly=True)

    @api.onchange('period_stop')
    def onchange_period_stop(self):
        if self.period_stop:
            self.accounting_yearend = (self.period_stop == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            self.date = fields.Date.to_string(fields.Date.from_string(self.period_stop.date_stop) + timedelta(days=12))
            self.name = '%s %s - %s' % (self._report_name,self.env['account.period'].period2month(self.period_start),self.env['account.period'].period2month(self.period_stop))

    line_ids = fields.One2many(comodel_name='account.declaration.line',inverse_name="declaration_id")
    @api.one
    def _move_ids_count(self):
        self.move_ids_count = len(self.move_ids)
    move_ids_count = fields.Integer(compute='_move_ids_count')
    @api.one
    def _payment_ids_count(self):
        self.payment_ids_count = len(self.get_payment_orders())
    payment_ids_count = fields.Integer(compute='_payment_ids_count')

    @api.multi
    def show_journal_entries(self):
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_stop.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
        action.update({
            'display_name': _('Verifikat'),
            'domain': [('id', 'in', self.move_ids.mapped('id'))],
            'context': ctx,
        })
        return action

    @api.multi
    def get_payment_orders(self):
        payment_order = []
        if self.move_id:
            for l in self.move_id.line_ids:
                line = self.env['account.payment.line'].search([('move_line_id', '=', l.id)])
                if line:
                    payment_order.append(line.order_id.id)
        return payment_order

    @api.multi
    def show_payment_orders(self):
        action = self.env['ir.actions.act_window'].for_xml_id('account_payment_order', 'account_payment_order_outbound_action')
        action.update({
            'display_name': _('%s') %self.name,
            'domain': [('id', 'in', self.get_payment_orders())],
        })
        return action

    @api.model
    def get_next_periods(self,length=3):
        last_declaration = self.search([],order='date_stop desc',limit=1)
        _logger.warn('get_netx_period date_stop %s >>> %s | %s' % (last_declaration.date_stop,self.search([],order='date_stop asc').mapped('name'),self.search([],order='date_stop desc').mapped('name')))
        return self.env['account.period'].get_next_periods(last_declaration.period_stop if last_declaration else None, int(self.env['ir.config_parameter'].get_param(key='l10n_se_tax_report.vat_declaration_frequency', default=str(length))))

    @api.one
    def do_draft(self):
        if self.move_id and self.move_id.state != 'draft':
            raise Warning('Deklarationen är bokförd, kan inte dras tillbaka i detta läge')
        self.line_ids.unlink()
        for move in self.move_ids:
            move.vat_declaration_id = None
        if self.move_id:
            if self.move_id.state == 'draft':
                self.move_id.unlink()
            else:
                raise Warning(_('Cannot recalculate.'))
        self.eskd_file = None
        self.state = 'draft'

    @api.one
    def do_cancel(self):
        if self.move_id and self.move_id.state != 'draft':
            raise Warning('Deklarationen är bokförd, kan inte avbryta i detta läge')
        # ~ self.line_ids.unlink()
        for move in self.move_ids:
            move.vat_declaration_id = None
        if self.move_id:
            self.move_id.unlink()
        self.eskd_file = None
        self.state = 'canceled'

    @api.one
    def calculate(self): # make a short cut to print financial report
        pass

    @api.one
    def create_event(self):
        #TODO create bokförings categ_ids
        if self.event_id and self.date:
            self.event_id.write({'start': self.date, 'stop': self.date})
        elif self.date:
            self.event_id = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create({
                        'name': self.name,
                        'description': 'Planned date for VAT-declaration',
                        'start': self.date,
                        'stop': self.date,
                        #'start_datetime': self.date,
                        #'stop_datetime': self.date,
                        #'partner_ids': [(6, 0, [int(partner)])],
                        'allday': True,
                        'duration': 8,
                        'categ_ids': [(6, 0, [self.env.ref('l10n_se_tax_report.categ_accounting').id])],
                        'state': 'open',            # to block that meeting date in the calendar
                        'privacy': 'confidential',
                    })

    @api.model
    def create(self,vals):
        if vals.get('period_stop'):
            if vals.get('period_start') != vals.get('period_stop'):
                vals['name'] = '%s %s - %s' % (self._report_name,self.env['account.period'].period2month(vals.get('period_start')),self.env['account.period'].period2month(vals.get('period_stop')))
            else:
                vals['name'] = '%s %s' % (self._report_name,self.env['account.period'].period2month(vals.get('period_start')))
            vals['date'] = fields.Date.to_string(fields.Date.from_string(self.env['account.period'].browse(vals['period_stop']).date_stop) + timedelta(days=12))
            vals['accounting_yearend'] = (self.env['account.period'].browse(vals['period_stop']) == self.env['account.fiscalyear'].browse(vals.get('fiscalyear_id')).period_ids[-1] if vals.get('fiscalyear_id') else None)
        res = super(account_declaration, self).create(vals)
        if vals.get('date'):
            res.create_event()
        return res

    @api.multi
    def write(self,values):
        res = super(account_declaration,self).write(values)
        if values.get('date'):
            self.create_event()
        return res

    @api.multi
    def unlink(self):
        for s in self:
            if s.event_id:
                s.event_id.unlink()
            res = super(account_declaration,s).unlink()
        return res

class account_vat_declaration(models.Model):
    _name = 'account.vat.declaration'
    _inherit = ['account.declaration']
    _report_name = 'Moms'

    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,default=_period_start)
    def _period_stop(self):
        return  self.get_next_periods()[1]
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period', required=True,default=_period_stop)

    @api.onchange('period_start', 'period_stop', 'target_move','accounting_method','accounting_yearend')
    def _vat(self):
        for decl in self:
            if decl.period_start and decl.period_stop:
                ctx = {
                    'period_start': decl.period_start.id,
                    'period_stop': decl.period_stop.id,
                    'accounting_yearend': decl.accounting_yearend,
                    'accounting_method': decl.accounting_method,
                    'target_move': decl.target_move,
                }
                decl.vat_momsingavdr = round(sum([self.env.ref('l10n_se_tax_report.%s' % row).with_context(ctx).sum_tax_period() for row in [48]])) * -1.0
                decl.vat_momsutg = round(sum([tax.with_context(ctx).sum_period for row in [10,11,12,30,31,32,60,61,62] for tax in self.env.ref('l10n_se_tax_report.%s' % row).mapped('tax_ids')])) * -1.0
                decl.vat_momsbetala = decl.vat_momsutg + decl.vat_momsingavdr
    vat_momsingavdr = fields.Float(string='Vat In', default=0.0, compute="_vat", help='Avläsning av transationer från baskontoplanen.')
    vat_momsutg = fields.Float(string='Vat Out', default=0.0, compute="_vat", help='Avläsning av transationer från baskontoplanen.')
    vat_momsbetala = fields.Float(string='Moms att betala ut (+) eller få tillbaka (-)', default=0.0, compute="_vat", help='Avläsning av skattekonto.')
    move_ids = fields.One2many(comodel_name='account.move',inverse_name="vat_declaration_id")

    @api.multi
    def show_momsingavdr(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT In'),
            'domain': [('id', 'in',self.env.ref('l10n_se_tax_report.48').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action

    @api.multi
    def show_momsutg(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_stop.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Out'),
            'domain': [('id', 'in', [line.id for row in [10,11,12,30,31,32,60,61,62] for line in self.env.ref('l10n_se_tax_report.%s' % row).with_context(ctx).get_taxlines() ])],
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

        for row in [5,6,7,8,10,11,12,20,21,22,23,24,30,31,32,35,36,37,38,39,40,41,42,48,50,60,61,62]:
            line = self.env.ref('l10n_se_tax_report.%s' % row)
            self.env['account.declaration.line'].create({
                'declaration_id': self.id,
                'balance': (line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign or 0.0,
                'name': line.name,
                'level': line.level,
                'move_line_ids': [(6,0,line.with_context(ctx).get_moveline_ids())],
                'move_ids': [(6,0,line.with_context(ctx).get_taxlines().mapped('move_id').mapped('id'))],
                })

        ##
        #### Mark Used moves
        ##

        for move in self.env['account.move'].with_context(ctx).get_move():
            move.vat_declaration_id = self.id

        for move in self.move_ids:
            move.full_reconcile_id = move.line_ids.mapped('full_reconcile_id')[0].id if len(move.line_ids.mapped('full_reconcile_id')) > 0 else None

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
            for k,v in NAMEMAPPING.items():
                line = self.env.ref('l10n_se_tax_report.%s' % v)
                amount = str(int(abs(round(line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign) or 0))
                if not amount == '0':
                    tax = etree.SubElement(moms, k)
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
                
class account_declaration_line(models.Model):
    _name = 'account.declaration.line'

    declaration_id = fields.Many2one(comodel_name="account.declaration", string='Declatation')
    move_line_ids = fields.Many2many(comodel_name="account.move.line", string='Move Lines')
    # ~ report_id = fields.Many2one(comodel_name="account.financial.report")
    account_type = fields.Char(string='Account Type')
    balance = fields.Float(string='Balance')
    type = fields.Char(string='Type')
    name = fields.Char(string='Name')
    level = fields.Integer(string='Level')
    move_ids = fields.Many2many(comodel_name='account.move')

    @api.multi
    def show_move_lines(self):
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('%s') %self.name,
            'domain': [('id', 'in', self.move_line_ids.mapped('id'))],
        })
        return action


class account_move(models.Model):
    _inherit = 'account.move'

    vat_declaration_id = fields.Many2one(comodel_name="account.vat.declaration")
    full_reconcile_id = fields.Many2one(comodel_name='account.full.reconcile')

    @api.model
    def get_movelines(self):
        #TODO:Undantag icke fodringsverifikat
        #TODO:Kontrollera yearend och invoice samt första perioden
        period_start = self._context.get('period_start',self._context.get('period_id'))
        period_stop = self._context.get('period_stop',period_start)
        # date_start / date_stop
        domain = [('period_id','in',self.env['account.period'].get_period_ids(period_start,period_stop))]
        if self._context.get('target_move') and self._context.get('target_move') in ['draft', 'posted']:
            domain.append(tuple(('state', '=', self._context.get('target_move'))))
        if self._context.get('accounting_method','invoice') == 'invoice':
            # fakturametoden
            lines = self.env['account.move'].search(domain).mapped('line_ids')
        else:
            # bokslutsmetoden / kontantmetoden
            # TODO:första perioden, betalningar som gäller fodringar som gäller föregående år skall inte ingå.
            moves = self.env['account.move'].search(domain)
            if self._context.get('accounting_yearend'):
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids])).mapped('line_ids')
            else:
                moves_19 = self.env['account.move'].search(domain).mapped('line_ids').filtered(lambda l: l.account_id.code[:2] == '19').mapped('move_id')
                reconciled_lines = moves_19.mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').filtered(lambda m: m.period_id.date_start <= self.env['account.period'].browse(period_stop).date_start).mapped('line_ids') # Alla 19x account.line 1804/06 -> account.move -> A-id -> account.line -> account.tax utom betalningar i framtiden
                lines = reconciled_lines | moves_19.mapped('line_ids').filtered(lambda l: l.tax_ids != False) # Alla 19x account.move.line med tax_line_id

            #~ lines = self.env['account.move'].search(domain)
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('line_ids')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('full_reconcile_id')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('reconciled_line_ids')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('move_id')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('line_ids')

        return lines

    @api.model
    def get_move(self):
        return self.get_movelines().mapped('move_id')
