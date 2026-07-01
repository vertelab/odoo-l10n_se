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
from odoo.exceptions import UserError
import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from workalendar.europe import Sweden
import requests
import logging
import os
import tempfile

_logger = logging.getLogger(__name__)

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


    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id, required=True)
    name = fields.Char(required=True)
    date = fields.Date(string='Declaration Date',
        help="Planned date, date when to report to the Skatteverket or do the declaration. Usually Monday second week "
             "after period, but check calendar at Skatteverket. (January and August differ.)")
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')],
        default='draft')

    target_move = fields.Selection(
        selection=[('posted', 'All Posted Entries'), ('draft', 'All Unposted Entries'), ('all', 'All Entries')],
        default='posted', string='Target Moves')

    accounting_method = fields.Selection(
        selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden')],
        related='company_id.accounting_method')

    accounting_yearend = fields.Boolean(string="Bokslutsperiod",
                                        help="I bokslutsperioden skall även utestående fordringar ingå i "
                                             "momsredovisningen vid kontantmetoden")
                                             
    free_text = fields.Text(string='Upplysningstext')
    report_file = fields.Binary(string="Report-file", readonly=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Verifikat', readonly=True)
    event_id = fields.Many2one(comodel_name='calendar.event', readonly=True)

    # --- Skatteverket API fields (shared across all declaration types) ---
    skv_api_status = fields.Selection(
        selection=[('draft', 'Not Submitted'), ('submitted', 'Submitted'),
                   ('error', 'Error'), ('accepted', 'Accepted')],
        string='SKV API Status',
        default='draft',
        help="Status of the submission to Skatteverket's API.")
    skv_response = fields.Text(
        string='SKV Response',
        help="Response text from Skatteverket API (shown on error).")
    skv_submitted_date = fields.Datetime(
        string='SKV Submitted Date',
        help="When the declaration was submitted to Skatteverket.")

    date_start = fields.Date(required=True)
    date_stop = fields.Date(required=True)

    @api.onchange('date_start', 'date_stop')
    def onchange_date(self):
        self.name = '%s %s - %s' % (self._report_name, self.date_start, self.date_stop)

    def _move_ids_count(self):
        for rec in self:
            self.move_ids_count = len(self.move_ids)

    move_ids_count = fields.Integer(compute='_move_ids_count')

    def _payment_ids_count(self):
        for rec in self:
            self.payment_ids_count = len(self.get_payment_orders())

    payment_ids_count = fields.Integer(compute='_payment_ids_count')

    def get_payment_orders(self):
        payment_order = []
        if self.move_id:
            for l in self.move_id.line_ids:
                line = self.env['account.payment.line'].search([('move_line_id', '=', l.id)])
                if line:
                    payment_order.append(line.order_id.id)
        return payment_order

    def show_payment_orders(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account_payment_order.account_payment_order_outbound_action')
        action.update({
            'display_name': _('%s') % self.name,
            'domain': [('id', 'in', self.get_payment_orders())],
        })
        return action

    # ~ @api.model
    # ~ def get_next_periods(self, length=3):
        # ~ last_declaration = self.search([], order='date_stop desc', limit=1)
        # ~ icp = self.env['ir.config_parameter'].sudo()
        # ~ freq_str = icp.get_param('l10n_se_tax_report.vat_declaration_frequency', default='quarter')
        # ~ if freq_str:
            # ~ _logger.warning(f"{freq_str=}")
            # ~ if freq_str == "month":
                # ~ freq_no = 1
            # ~ if freq_str == "quarter":
                # ~ freq_no = 3
            # ~ if freq_str == "year":
                # ~ freq_no = 12
            # ~ return self.env['account.period'].get_next_periods(
                # ~ last_declaration.period_stop if last_declaration else None, freq_no)
                
                
    @api.model
    def get_next_dates(self, length=3):
        last_declaration = self.search([], order='date_stop desc', limit=1)
        freq_str = self.env.company.vat_declaration_frequency or 'quarter'
        _logger.warning(f"{freq_str=}")
        if freq_str == "month":
            freq_no = 1
        elif freq_str == "year":
            freq_no = 12
        else:
            freq_no = 3
        return [last_declaration.start_date.replace(day=1) + relativedelta(months=freq_no), last_declaration.start_date.replace(day=1) + relativedelta(months=freq_no+1)]

    def do_draft(self):
        for rec in self:
            if self.move_id and self.move_id.state != 'draft':
                raise UserError('The declaration has been posted and cannot be withdrawn at this stage.')
            self.line_ids.unlink()
            if self.move_id:
                if self.move_id.state == 'draft':
                    self.move_id.unlink()
                else:
                    raise UserError(_('Cannot recalculate.'))
            self.state = 'draft'

    def do_cancel(self):
        for rec in self:
            if self.move_id and self.move_id.state != 'draft':
                raise UserError('The declaration has been posted and cannot be canceled at this stage.')
            # ~ self.line_ids.unlink()
            if self.move_id:
                self.move_id.unlink()
            self.state = 'canceled'

    def do_done(self):
        for rec in self:
            self.state = 'done'

    def calculate(self):  # make a short cut to print financial report
        for rec in self:
            pass

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

    @api.model
    def _calculate_vat_deadline(self, date_stop, freq_months):
        """Calculate the VAT declaration deadline.

        Swedish rules (Skatteverket):
        - Monthly: 12th day of the SECOND month after the period.
          e.g. January → March 12, February → April 12.
          This gives ~42-45 days from period end.
        - Quarterly: 12th day of the second month after the quarter.
          e.g. Q1 (Jan-Mar) → May 12.
        - Annual: 12th day of the second month after year-end.
        """
        # All periods (monthly, quarterly, annual) use the same rule:
        # the 12th of the SECOND month after the period end.
        # Monthly example: January 31 → March 12 (~40 days).
        cal = Sweden()
        deadline = date_stop + relativedelta(months=2, day=12)
        while not cal.is_working_day(deadline):
            deadline += timedelta(days=1)
        return deadline

    # --- Skatteverket API helper methods (shared across all declaration types) ---

    def _get_skv_settings(self):
        """Retrieve Skatteverket API settings from company."""
        company = self.company_id or self.env.company
        return {
            'test_mode': company.skv_test_mode,
            'auth_method': company.skv_auth_method,
            'api_url': company.skv_api_url,
            'auth_url': company.skv_auth_url,
            'token_url': company.skv_token_url,
        }

    def _get_skv_partner(self):
        """Find the Skatteverket partner configured for API access."""
        partner = self.env['res.partner'].search(
            [('enable_skatteverket_api', '=', True)], limit=1)
        if not partner:
            partner = self.env.ref('l10n_se_tax_report.res_partner-SKV', raise_if_not_found=False)
        return partner

    def _get_skv_access_token(self, partner):
        """Obtain an access token for Skatteverket API."""
        if partner.check_valid_access_token():
            return partner.access_token

        settings = self._get_skv_settings()

        if settings['auth_method'] == 'cert':
            if not partner.certificate:
                raise UserError(_(
                    "No certificate uploaded on the Skatteverket partner. "
                    "Upload a certificate on the partner record."))
            cert_data = base64.b64decode(partner.certificate)
            tmp = tempfile.NamedTemporaryFile(suffix='.pem', delete=False)
            tmp.write(cert_data)
            tmp.close()
            session = requests.Session()
            session.cert = tmp.name

            try:
                resp = session.post(
                    settings['token_url'],
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': partner.oauth_client_id or '',
                        'client_secret': partner.oauth_secret or '',
                        'scope': 'ska',
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    partner.write({
                        'access_token': token_data.get('access_token'),
                        'recived_token_on': datetime.now(),
                        'expires_in': token_data.get('expires_in', 3600),
                    })
                    return token_data.get('access_token')
                else:
                    _logger.error("SKV token error: %s %s", resp.status_code, resp.text)
                    raise UserError(_(
                        "Failed to get access token from Skatteverket: %s")
                        % resp.text[:200])
            finally:
                os.unlink(tmp.name)
        else:
            raise UserError(_(
                "E-identification flow requires interactive browser. "
                "Please use certificate authentication or complete "
                "OAuth2 authorization via the Tax Account module first."))

    def action_send_to_skv(self):
        """Submit declaration to Skatteverket API. Override in subclass."""
        raise NotImplementedError(_(
            "SKV API submission not implemented for this declaration type."))


class account_declaration_line_id(models.Model):
    _name = 'account.declaration.line.id'
    _description = 'Account declaration line id'


class account_vat_declaration(models.Model):
    _name = 'account.vat.declaration'
    _inherit = 'account.declaration'
    _description = 'Moms Declaration Report'
    _report_name = 'Moms'

    def _date_start(self):
        return self.get_next_dates()[0]

    def _date_stop(self):
        return self.get_next_dates()[1]

    
    vat_momsingavdr = fields.Integer(string='Vat In', default=0, compute="_vat",
                                     help='Avläsning av transationer från baskontoplanen.')
    vat_momsutg = fields.Integer(string='Vat Out', default=0, compute="_vat",
                                 help='Avläsning av transationer från baskontoplanen.')
    vat_momsbetala = fields.Integer(string='Moms att betala ut (+) eller få tillbaka (-)', default=0, compute="_vat",
                                    help='Avläsning av skattekonto.')

    date = fields.Date(compute='_compute_date', inverse='_inverse_date', store=True)

    move_ids = fields.One2many(comodel_name='account.move', inverse_name="vat_declaration_id")
    line_ids = fields.One2many(comodel_name='account.declaration.line', inverse_name="vat_declaration_id")

    @api.depends('date_stop')
    def _compute_date(self):
        for record in self:
            if record.date_stop:
                freq_str = record.company_id.vat_declaration_frequency or 'quarter'
                freq_map = {'month': 1, 'quarter': 3, 'year': 12}
                freq_months = freq_map.get(freq_str, 3)
                record.date = self._calculate_vat_deadline(
                    fields.Date.from_string(record.date_stop), freq_months)
            else:
                record.date = False

    def _inverse_date(self):
        pass

    def write(self, values):
        """Override to update calendar event when date_stop (and thus date) changes.
        Since date is a computed stored field based on date_stop, the parent write()
        won't see 'date' in values and won't trigger create_event(). We handle it here."""
        res = super(account_vat_declaration, self).write(values)
        if values.get('date_stop') or values.get('date'):
            self.create_event()
        return res

    def comfirm_declaration(self):  # Atm just moves the report from draf to Confirmend
        self.write({"state": "confirmed"})
        # for rec in self:
        #     self.state = 'confirmed'

    @api.model
    def _cron_create_vat_declaration(self):
        freq_str = self.env.company.vat_declaration_frequency
        if not freq_str:
            return False
        freq_map = {'month': 1, 'quarter': 3, 'year': 12}
        freq_months = freq_map.get(freq_str, 3)

        last = self.search([], order='date_stop desc', limit=1)
        if last:
            date_start = fields.Date.from_string(last.date_stop) + timedelta(days=1)
        else:
            today = fields.Date.today()
            date_start = today.replace(month=1, day=1)

        date_stop = date_start + relativedelta(months=freq_months, days=-1)
        date_deadline = self._calculate_vat_deadline(date_stop, freq_months)

        existing = self.search([
            ('date_start', '=', fields.Date.to_string(date_start)),
            ('date_stop', '=', fields.Date.to_string(date_stop)),
        ], limit=1)
        if existing:
            return False

        report = self.env.company.vat_report_template_id or self.env.ref('l10n_se_mis.report_md')

        fiscalyear = self.env['account.fiscalyear'].search([
            ('date_start', '<=', date_start),
            ('date_stop', '>=', date_stop),
        ], limit=1)

        name = '%s %s - %s' % (self._report_name, date_start, date_stop)
        declaration = self.create({
            'name': name,
            'date_start': fields.Date.to_string(date_start),
            'date_stop': fields.Date.to_string(date_stop),
            'date': fields.Date.to_string(date_deadline),
            'report_id': report.id,
            'accounting_yearend': fiscalyear and date_stop >= fiscalyear.date_stop,
        })

        if declaration:
            declaration.create_event()  # Ensure calendar event is created for cron-created declarations
            declaration.calculate()
        return True


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

