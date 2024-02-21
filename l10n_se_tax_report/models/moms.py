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
from odoo.exceptions import Warning, UserError
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
    ('ForsMomsEjAnnan', 5),  # 05: Momspliktig försäljning som inte ingår i annan ruta nedan
    ('UttagMoms', 6),  # 06: Momspliktiga uttag
    ('UlagMargbesk', 7),  # 07: Beskattningsunderlag vid vinstmarginalbeskattning
    ('HyrinkomstFriv', 8),  # 08: Hyresinkomster vid frivillig skattskyldighet
    ('InkopVaruAnnatEg', 20),  # 20: Inköp av varor från annat EU-land
    ('InkopTjanstAnnatEg', 21),  # 21: Inköp av tjänster från annat EU-land
    ('InkopTjanstUtomEg', 22),  # 22: Inköp av tjänster från land utanför EU
    ('InkopVaruSverige', 23),  # 23: Inköp av varor i Sverige
    ('InkopTjanstSverige', 24),  # 24: Inköp av tjänster i Sverige
    ('MomsUlagImport', 50),  # 50: Beskattningsunderlag vid import
    ('ForsVaruAnnatEg', 35),  # 35: Försäljning av varor till annat EU-land
    ('ForsVaruUtomEg', 36),  # 36: Försäljning av varor utanför EU
    ('InkopVaruMellan3p', 37),  # 37: Mellanmans inköp av varor vid trepartshandel
    ('ForsVaruMellan3p', 38),  # 38: Mellanmans försäljning av varor vid trepartshandel
    ('ForsTjSkskAnnatEg', 39),  # 39: Försäljning av tjänster när köparen är skattskyldig i annat EU-land
    ('ForsTjOvrUtomEg', 40),  # 40: Övrig försäljning av tjänster omsatta utom landet
    ('ForsKopareSkskSverige', 41),  # 41: Försäljning när köparen är skattskyldig i Sverige
    ('ForsOvrigt', 42),  # 42: Övrig försäljning m.m. ???
    ('MomsUtgHog', 10),  # 10: Utgående moms 25 %
    ('MomsUtgMedel', 11),  # 11: Utgående moms 12 %
    ('MomsUtgLag', 12),  # 12: Utgående moms 6 %
    ('MomsInkopUtgHog', 30),  # 30: Utgående moms 25%
    ('MomsInkopUtgMedel', 31),  # 31: Utgående moms 12%
    ('MomsInkopUtgLag', 32),  # 32: Utgående moms 6%
    ('MomsImportUtgHog', 60),  # 60: Utgående moms 25%
    ('MomsImportUtgMedel', 61),  # 61: Utgående moms 12%
    ('MomsImportUtgLag', 62),  # 62: Utgående moms 6%
    ('MomsIngAvdr', 48),  # 48: Ingående moms att dra av
    #    ('MomsBetala', 49),             #49: Moms att betala eller få tillbaka | hard coded
])


class account_declaration(models.Model):
    _name = 'account.declaration'
    _inherit = ['mail.thread']
    _description = 'Declaration Report'
    _report_name = 'Declaration Report'
    _order = 'date asc'

    def _fiscalyear_id(self):
        return self.env['account.fiscalyear'].search(
            [('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    def _period_start(self):
        return self.get_next_periods()[0]

    def _accounting_method(self):
        self = self.sudo()
        return self.env['ir.config_parameter'].get_param(key='l10n_se_tax_report.accounting_method', default='invoice')
        
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id, required=True)
    name = fields.Char()
    date = fields.Date(
        help="Planned date, date when to report to the Skatteverket or do the declaration. Usually Monday second week "
             "after period, but check calendar at Skatteverket. (January and August differ.)")
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')],
        default='draft')  # TODO,track_visibility='onchange')
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string=u'Räkenskapsår',
                                    help='Håll tom för alla öppna räkenskapsår', default=_fiscalyear_id)
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True)
    # ~ period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,
    # default=_period_start)
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period')
    # ~ period_stop = fields.Many2one(comodel_name='account.period', string='Slut period',default=_period_start)
    target_move = fields.Selection(
        selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')],
        default='posted', string='Target Moves')
    accounting_method = fields.Selection(selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'), ],
                                         default=_accounting_method, string='Redovisningsmetod',
                                         help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden "
                                              "skall välja fakturametoden i sista perioden/bokslutsperioden")
    accounting_yearend = fields.Boolean(string="Bokslutsperiod",
                                        help="I bokslutsperioden skall även utestående fordringar ingå i "
                                             "momsredovisningen vid kontantmetoden")
    free_text = fields.Text(string='Upplysningstext')
    report_file = fields.Binary(string="Report-file", readonly=True)
    eskd_file = fields.Binary(string="eSKD-file", readonly=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat', readonly=True)
    date_stop = fields.Date(related='period_start.date_stop', store=True)
    event_id = fields.Many2one(comodel_name='calendar.event', readonly=True)

    @api.onchange('period_stop')
    def onchange_period_stop(self):
        # ~ raise Warning(self._name)
        if self.period_stop and (self._name == 'account.declaration' or self._name == 'account.vat.declaration'):
            self.accounting_yearend = (
                self.period_stop == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            d = fields.Date.from_string(self.period_stop.date_stop)
            intDay = 12
            intMonth = d.month + 2
            intYear = d.year
            if intMonth > 12:
                intMonth -= 12
                intYear = intYear + 1
            # 17 = winter and summer.
            if intMonth == 1 or intMonth == 8:
                intDay = 17

            # create the new date:
            # ~ raise Warning(intMonth)
            newdate = datetime(intYear, intMonth, intDay)
            if newdate.weekday() == 5:
                newdate + timedelta(days=2)
            if newdate.weekday() == 6:
                newdate + timedelta(days=1)
            _logger.warning('newdate = %s' % newdate)
            self.date = fields.Date.to_string(newdate)
            self.name = '%s %s - %s' % (self._report_name, self.env['account.period'].period2month(self.period_start),
                                        self.env['account.period'].period2month(self.period_stop))

    # ~ @api.one
    def _move_ids_count(self):
        for rec in self:
            self.move_ids_count = len(self.move_ids)

    move_ids_count = fields.Integer(compute='_move_ids_count')

    # ~ @api.one
    def _payment_ids_count(self):
        for rec in self:
            self.payment_ids_count = len(self.get_payment_orders())

    payment_ids_count = fields.Integer(compute='_payment_ids_count')

    # ~ @api.multi
    def get_payment_orders(self):
        payment_order = []
        if self.move_id:
            for l in self.move_id.line_ids:
                line = self.env['account.payment.line'].search([('move_line_id', '=', l.id)])
                if line:
                    payment_order.append(line.order_id.id)
        return payment_order

    # ~ @api.multi
    def show_payment_orders(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account_payment_order.account_payment_order_outbound_action')
        action.update({
            'display_name': _('%s') % self.name,
            'domain': [('id', 'in', self.get_payment_orders())],
        })
        return action

    # ~ @api.model
    # ~ def get_next_periods(self,length=3):
    # ~ last_declaration = self.search([],order='date_stop desc',limit=1)
    # ~ return self.env['account.period'].get_next_periods(last_declaration.period_stop if last_declaration else None, int(self.env['ir.config_parameter'].get_param(key='l10n_se_tax_report.vat_declaration_frequency', default=str(length))))

    @api.model
    def get_next_periods(self, length=3):
        last_declaration = self.search([], order='date_stop desc', limit=1)
        icp = self.env['ir.config_parameter'].sudo()
        freq_str = icp.get_param('l10n_se_tax_report.vat_declaration_frequency', default='quarter')
        if freq_str:
            _logger.warning(f"{freq_str=}")
            if freq_str == "month":
                freq_no = 1
            if freq_str == "quarter":
                freq_no = 3
            if freq_str == "year":
                freq_no = 12
            return self.env['account.period'].get_next_periods(
                last_declaration.period_stop if last_declaration else None, freq_no)

    # ~ @api.one
    def do_draft(self):
        for rec in self:
            if self.move_id and self.move_id.state != 'draft':
                raise Warning('Deklarationen är bokförd, kan inte dras tillbaka i detta läge')
            self.line_ids.unlink()
            if self.move_id:
                if self.move_id.state == 'draft':
                    self.move_id.unlink()
                else:
                    raise Warning(_('Cannot recalculate.'))
            self.eskd_file = None
            self.state = 'draft'

    # ~ @api.one
    def do_cancel(self):
        for rec in self:
            if self.move_id and self.move_id.state != 'draft':
                raise Warning('Deklarationen är bokförd, kan inte avbryta i detta läge')
            # ~ self.line_ids.unlink()
            if self.move_id:
                self.move_id.unlink()
            self.eskd_file = None
            self.state = 'canceled'

    # ~ @api.one
    def do_done(self):
        for rec in self:
            self.state = 'done'

    # ~ @api.one
    def calculate(self):  # make a short cut to print financial report
        for rec in self:
            pass

    # ~ @api.one
    def create_event(self):
        for rec in self:
            # TODO create bokförings categ_ids
            if self.event_id and self.date:
                self.event_id.write({'start': self.date, 'stop': self.date})
            elif self.date:
                self.event_id = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create({
                    'name': self.name,
                    'description': 'Planned date for VAT-declaration',
                    'start': self.date,
                    'stop': self.date,
                    # 'start_datetime': self.date,
                    # 'stop_datetime': self.date,
                    # 'partner_ids': [(6, 0, [int(partner)])],
                    'allday': True,
                    'duration': 8,
                    'categ_ids': [(6, 0, [self.env.ref('l10n_se_tax_report.categ_accounting').id])],
                    # ~ 'state': 'open',            # to block that meeting date in the calendar
                    'privacy': 'confidential',
                })

    @api.model
    def create(self, vals):
        # ~ if vals.get('period_stop'):
        # ~ if vals.get('period_start') != vals.get('period_stop'):
        # ~ vals['name'] = '%s %s - %s' % (self._report_name,self.env['account.period'].period2month(vals.get('period_start')),self.env['account.period'].period2month(vals.get('period_stop')))
        # ~ else:
        # ~ vals['name'] = '%s %s' % (self._report_name,self.env['account.period'].period2month(vals.get('period_start')))
        # ~ vals['accounting_yearend'] = (self.env['account.period'].browse(vals['period_stop']) == self.env['account.fiscalyear'].browse(vals.get('fiscalyear_id')).period_ids[-1] if vals.get('fiscalyear_id') else None)
        res = super(account_declaration, self).create(vals)
        if vals.get('date'):
            res.create_event()
        return res

    # ~ @api.multi
    def write(self, values):
        res = super(account_declaration, self).write(values)
        if values.get('date'):
            self.create_event()
        return res

    # ~ @api.multi
    def unlink(self):
        for s in self:
            if s.event_id:
                s.event_id.unlink()
            res = super(account_declaration, s).unlink()
        return res

    @api.model
    def next_monday(self, date, day=0):
        return date + timedelta(days=(day - date.weekday() + 7) % 7)
    # ~ onDay = lambda date, day: date + datetime.timedelta(days=(day-date.weekday()+7)%7)


class account_declaration_line_id(models.Model):
    _name = 'account.declaration.line.id'
    _description = 'Account declaration line id'


class account_vat_declaration(models.Model):
    _name = 'account.vat.declaration'
    _inherit = 'account.declaration'
    _description = 'Moms Declaration Report'
    _report_name = 'Moms'

    def _period_start(self):
        return self.get_next_periods()[0]

    def _period_stop(self):
        return self.get_next_periods()[1]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,
                                   default=_period_start)
    period_stop = fields.Many2one(comodel_name='account.period', string='Slut period', required=True,
                                  default=_period_stop)
    
    vat_momsingavdr = fields.Float(string='Vat In', default=0.0, compute="_vat",
                                   help='Avläsning av transationer från baskontoplanen.')
    vat_momsutg = fields.Float(string='Vat Out', default=0.0, compute="_vat",
                               help='Avläsning av transationer från baskontoplanen.')
    vat_momsbetala = fields.Float(string='Moms att betala ut (+) eller få tillbaka (-)', default=0.0, compute="_vat",
                                  help='Avläsning av skattekonto.')

    move_ids = fields.One2many(comodel_name='account.move', inverse_name="vat_declaration_id")
    line_ids = fields.One2many(comodel_name='account.declaration.line', inverse_name="vat_declaration_id")

    @api.model
    def get_next_periods(self, length=3):
        last_declaration = self.search([], order='date_stop desc', limit=1)
        icp = self.env['ir.config_parameter'].sudo()
        freq_str = icp.get_param('l10n_se_tax_report.vat_declaration_frequency', default='quarter')
        if freq_str:
            _logger.warning(f"{freq_str=}")
            if freq_str == "month":
                freq_no = 1
            if freq_str == "quarter":
                freq_no = 3
            if freq_str == "year":
                freq_no = 12
            return self.env['account.period'].get_next_periods(
                last_declaration.period_stop if last_declaration else None, freq_no)

    def comfirm_declaration(self):  # Atm just moves the report from draf to Confirmend
        for rec in self:
            self.state = 'confirmed'


class account_declaration_line(models.Model):
    _name = 'account.declaration.line'
    _description = 'Lines belonging to account declaration'

    declaration_id = fields.Many2one(comodel_name="account.declaration.line.id", string='Declaration')
    move_line_ids = fields.Many2many(comodel_name="account.move.line", string='Move Lines')
    account_type = fields.Char(string='Account Type')
    balance = fields.Integer(string='Balance')
    type = fields.Char(string='Type')
    name = fields.Char(string='Name')
    level = fields.Integer(string='Level')
    move_ids = fields.Many2many(comodel_name='account.move')
    vat_declaration_id = fields.Many2one(comodel_name="account.vat.declaration")

    def show_move_lines(self):
        _logger.warning('jakmar: implement/change me')


class account_move(models.Model):
    _inherit = 'account.move'

    vat_declaration_id = fields.Many2one(comodel_name="account.vat.declaration")
    full_reconcile_id = fields.Many2one(comodel_name='account.full.reconcile')
    year_end_move = fields.Boolean(string='Year End Move', default=False)

    @api.model
    def get_movelines(self):
        # TODO:Undantag icke fodringsverifikat
        # TODO:Kontrollera yearend och invoice samt första perioden
        period_start = self._context.get('period_start', self._context.get('period_id'))
        period_stop = self._context.get('period_stop', period_start)
        # date_start / date_stop
        domain = [('period_id', 'in', self.env['account.period'].get_period_ids(period_start, period_stop))]
        if self._context.get('target_move') and self._context.get('target_move') in ['draft', 'posted']:
            domain.append(tuple(('state', '=', self._context.get('target_move'))))
        if self._context.get('accounting_method', 'invoice') == 'invoice':
            # fakturametoden
            lines = self.env['account.move'].search(domain).mapped('line_ids')
        else:
            # bokslutsmetoden / kontantmetoden
            # TODO:första perioden, betalningar som gäller fodringar som gäller föregående år skall inte ingå.
            moves = self.env['account.move'].search(domain)
            if self._context.get('accounting_yearend'):
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped(
                    'line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped(
                    'line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids])).mapped(
                    'line_ids')
                for move in moves:
                    move.year_end_move = True
            else:
                moves_19 = self.env['account.move'].search(domain).mapped('line_ids').filtered(
                    lambda l: l.account_id.code[:2] in ['19', '28']).mapped('move_id')
                # ~ raise Warning(moves_19.mapped('name'))
                reconciled_lines = moves_19.mapped('line_ids').mapped('full_reconcile_id').mapped(
                    'reconciled_line_ids').mapped('move_id').filtered(
                    lambda m: m.year_end_move == False and m.period_id.date_start <= self.env['account.period'].browse(
                        period_stop).date_start).mapped(
                    'line_ids')  # Alla 19x account.line 1804/06 -> account.move -> A-id -> account.line -> account.tax utom betalningar i framtiden
                lines = reconciled_lines | moves_19.mapped('line_ids').filtered(
                    lambda l: l.tax_ids != False)  # Alla 19x account.move.line med tax_line_id

        return lines

    @api.model
    def get_move(self):
        return self.get_movelines().mapped('move_id')
