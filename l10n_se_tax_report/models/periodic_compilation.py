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


# order must be correct
TAGS = [
    'Supplied Goods',
    'Triangulation'
    'Services Supplied'
    
]

TAGS_NEW = {
    'AvdrPrelSkatt': '001', # Avdragen preliminärskatt
    'KontantErsattningUlagAG': '011', # Kontant bruttolön m.m.
    'SkatteplOvrigaFormanerUlagAG': '012', # Övriga skattepliktiga förmåner
    'SkatteplBilformanUlagAG': '013', # Skattepliktig bilförmån
    'AvdragUtgiftArbetet': '019', # Avdrag för utgifter i arbetet
    'Bilersattning': '050', # Bilersättning
    'UlagFoU': '470', # Underlag avdrag forskning och utveckling
    'AvdragFoU': '475', # Avdrag FoU
    'SummaArbAvgSlf': '487', # Summa arbetsgivaravgifter och SLF
    'SummaSkatteavdr': '497', # Summa skatteavdrag
}

class account_periodic_compilation(models.Model):
    _name = 'account.periodic.compilation'
    _inherits = {'account.declaration.line.id': 'line_id'}
    _inherit = 'account.declaration'
    _report_name = 'PeriodicCompilation'
    _order = 'date desc'

    line_id = fields.Many2one('account.declaration.line.id', auto_join=True, index=True, ondelete="cascade", required=True)
    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,default=_period_start)
    # ~ period_stop = fields.Many2one(comodel_name='account.period', string='Slut period',default=_period_stop)
    move_ids = fields.One2many(comodel_name='account.move',inverse_name="agd_declaration_id")
    line_ids = fields.One2many(comodel_name='account.declaration.line',inverse_name="agd_declaration_id")
    payslip_ids = fields.Many2many(comodel_name='hr.payslip', string='Payslips', compute='_payslip_ids')

    @api.onchange('period_start')
    def _payslip_ids(self):
        slips = self.env['hr.payslip'].search([('move_id.period_id.id','=',self.period_start.id)])
        self.payslip_ids = slips.mapped('id')

        # ~ _logger.warn('jakob ***  payslip ')

        self.move_ids = []
        for move in slips.mapped('move_id'):
            move.agd_declaration_id = self.id
        # ~ _logger.info('AGD: %s %s' % (slips.mapped('id'),slips.mapped('move_id.id')))
        
    @api.multi
    def show_journal_entries(self):
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_start.id,
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

    @api.onchange('period_start')
    def onchange_period_start(self):
        if self.period_start:
            # ~ self.accounting_yearend = (self.period_start == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            # ~ self.period_stop = self.period_start
            self.date = fields.Date.to_string(fields.Date.from_string(self.period_start.date_stop) + timedelta(days=12))
            self.name = '%s %s' % (self._report_name,self.env['account.period'].period2month(self.period_start,short=False))

    # ~ @api.onchange('period_start','target_move','accounting_method','accounting_yearend')
    @api.one
    def _vat(self):
        if self.period_start:
            ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
            self.SumSkAvdr = round(self.env.ref('l10n_se_tax_report.agd_report_SumSkAvdr').with_context(ctx).sum_tax_period()) * -1.0
            self.SumAvgBetala = round(self.env.ref('l10n_se_tax_report.agd_report_SumAvgBetala').with_context(ctx).sum_tax_period()) * -1.0
            self.ag_betala = self.SumAvgBetala + self.SumSkAvdr

    SumSkAvdr    = fields.Float(compute='_vat')
    SumAvgBetala = fields.Float(compute='_vat')
    ag_betala  = fields.Float(compute='_vat')

    @api.multi
    def show_SumSkAvdr(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in', self.env.ref('l10n_se_tax_report.agd_report_SumSkAvdr').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action

    @api.multi
    def show_SumAvgBetala(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in', self.env.ref('l10n_se_tax_report.agd_report_SumAvgBetala').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action

    @api.one
    def do_draft(self):
        super(account_agd_declaration, self).do_draft()
        self.slip_ids = []
        for move in self.move_ids:
            move.agd_declaration_id = None

    @api.one
    def do_cancel(self):
        super(account_agd_declaration, self).do_draft()
        for move in self.move_ids:
            move.agd_declaration_id = None

    @api.one
    def calculate(self): # make a short cut to print financial report
        if self.state not in ['draft']:
            raise Warning("Du kan inte beräkna i denna status, ändra till utkast")
        if self.state in ['draft']:
            self.state = 'confirmed'

        slips = self.env['hr.payslip'].search([('move_id.period_id.id','=',self.period_start.id)])
        self.payslip_ids = slips.mapped('id')
        self.move_ids = []
        for move in slips.mapped('move_id'):
            move.agd_declaration_id = self.id


        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_start.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
            'nix_journal_ids': [self.env.ref('l10n_se_tax_report.agd_journal').id]
        }

        self._vat()
        # ~ self.SumSkAvdr = round(self.env.ref('l10n_se_tax_report.agd_report_SumSkAvdr').with_context(ctx).sum_tax_period()) * -1.0
        # ~ self.SumAvgBetala = round(self.env.ref('l10n_se_tax_report.agd_report_SumAvgBetala').with_context(ctx).sum_tax_period()) * -1.0
        # ~ self.ag_betala = decl.SumAvgBetala + decl.SumSkAvdr

        # ~ raise Warning(self.env.ref('l10n_se_tax_report.agd_report_UlagAvgHel').with_context(ctx).get_moveline_ids() )
        ##
        ####  Create report lines
        ##

        for row in TAGS:
            line = self.env.ref('l10n_se_tax_report.agd_report_%s' % row)
            if not line:
                raise Warning(_('Report line missing %' % row))
            self.env['account.declaration.line'].create({
                'agd_declaration_id': self.id,
                'balance': int(abs(line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) or 0.0),
                'name': line.name,
                'level': line.level,
                'move_line_ids': [(6,0,line.with_context(ctx).get_moveline_ids())],
                })

        ##
        #### Mark Used moves
        ##

        # ~ for move in self.line_ids.mapped('move_line_ids').mapped('move_id'):
            # ~ if not move.agd_declaration_id:
                # ~ move.agd_declaration_id = self.id
            # ~ else:
                # ~ raise Warning(_('Move %s is already assigned to %s' % (move.name, move.agd_declaration_id.name)))

        ##
        #### Create eSDK-file
        ##

        # ~ tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('l10n_se.tax_group_hr').id), ('name', 'not in', ['eSKDUpload', 'Ag', 'AgBrutU', 'AgAvgU', 'AgAvgAv', 'AgAvg', 'AgAvd', 'AgAvdU', 'AgAvgPreS', 'AgPre', 'UlagVXLon', 'AvgVXLon'])])
        # ~ def parse_xml(recordsets):
            # ~ root = etree.Element('eSKDUpload', Version="6.0")
            # ~ orgnr = etree.SubElement(root, 'OrgNr')
            # ~ orgnr.text = self.env.user.company_id.company_registry
            # ~ ag = etree.SubElement(root, 'Ag')
            # ~ period = etree.SubElement(ag, 'Period')
            # ~ period.text = self.period_start.date_start[:4] + self.period_start.date_start[5:7]
            # ~ for row in TAGS:
                # ~ line = self.env.ref('l10n_se_tax_report.agd_report_%s' % row)
                # ~ tax = etree.SubElement(ag, row)
                # ~ tax.text = str(int(abs((line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign))) or '0'
            # ~ free_text = etree.SubElement(ag, 'TextUpplysningAg')
            # ~ free_text.text = self.free_text or ''
            # ~ return root
        # ~ xml = etree.tostring(parse_xml(tax_account), pretty_print=True, encoding="ISO-8859-1")
        # ~ xml = xml.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        # ~ self.eskd_file = base64.b64encode(xml)

        ### new version of agd from February 2019
        ### https://skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/tekniskbeskrivningochtesttjanst/tekniskbeskrivning114.4.2cf1b5cd163796a5c8ba79b.html

        tax_account = self.env['account.tax'].search([('tax_group_id', '=', self.env.ref('l10n_se.tax_group_hr').id), ('name', 'not in', ['eSKDUpload', 'Ag', 'AgBrutU', 'AgAvgU', 'AgAvgAv', 'AgAvg', 'AgAvd', 'AgAvdU', 'AgAvgPreS', 'AgPre', 'UlagVXLon', 'AvgVXLon'])])
        def parse_xml(recordsets):
            def get_tax_value(tax):
                line = self.env.ref('l10n_se_tax_report.agd_report_%s' % tax)
                return str(int(abs((line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) * line.sign))) or '0'
            namespaces = {
                'agd': "http://xmls.skatteverket.se/se/skatteverket/da/komponent/schema/1.1",
                'xsi': "http://www.w3.org/2001/XMLSchema-instance",
                None: "http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1",
            }
            ns = '{%s}' %namespaces['agd']
            company_registry = '16' + self.env.user.company_id.company_registry.replace('-', '')
            attrib={'{%s}schemaLocation' % namespaces['xsi']: "http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1 http://xmls.skatteverket.se/se/skatteverket/da/arbetsgivardeklaration/arbetsgivardeklaration_1.1.xsd", 'omrade': 'Arbetsgivardeklaration'}
            skatteverket = etree.Element('Skatteverket', attrib=attrib, nsmap=namespaces)
            avsandare = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.agd_avsandare')
            if not avsandare:
                raise Warning(_(u'Please configurate avsändare'))
            avsandare_dict = eval(avsandare)
            agd_avsandare = etree.SubElement(skatteverket, ns + 'Avsandare')
            agd_programnamn = etree.SubElement(agd_avsandare, ns + 'Programnamn')
            agd_programnamn.text = avsandare_dict.get('programnamn', '')
            agd_organisationsnummer = etree.SubElement(agd_avsandare, ns + 'Organisationsnummer')
            agd_organisationsnummer.text = '16' + avsandare_dict.get('organisationsnummer', '')

            agd_tekniskKontaktperson = etree.SubElement(agd_avsandare, ns + 'TekniskKontaktperson')
            agd_tekniskKontaktperson_agd_name = etree.SubElement(agd_tekniskKontaktperson, ns + 'Namn')
            agd_tekniskKontaktperson_agd_name.text = avsandare_dict.get('tk_name', '')
            agd_tekniskKontaktperson_agd_telefon = etree.SubElement(agd_tekniskKontaktperson, ns + 'Telefon')
            agd_tekniskKontaktperson_agd_telefon.text = avsandare_dict.get('tk_phone', '')
            agd_tekniskKontaktperson_agd_epostadress = etree.SubElement(agd_tekniskKontaktperson, ns + 'Epostadress')
            agd_tekniskKontaktperson_agd_epostadress.text = avsandare_dict.get('tk_email', '')
            agd_tekniskKontaktperson_agd_utdelningsadress1 = etree.SubElement(agd_tekniskKontaktperson, ns + 'Utdelningsadress1')
            agd_tekniskKontaktperson_agd_utdelningsadress1.text = avsandare_dict.get('tk_street', '')
            if avsandare_dict.get('tk_street2', ''):
                agd_tekniskKontaktperson_agd_utdelningsadress2 = etree.SubElement(agd_tekniskKontaktperson, ns + 'Utdelningsadress2')
                agd_tekniskKontaktperson_agd_utdelningsadress2.text = avsandare_dict.get('tk_street2', '')
            agd_tekniskKontaktperson_agd_postnummer = etree.SubElement(agd_tekniskKontaktperson, ns + 'Postnummer')
            agd_tekniskKontaktperson_agd_postnummer.text = avsandare_dict.get('tk_zip', '')
            agd_tekniskKontaktperson_agd_postort = etree.SubElement(agd_tekniskKontaktperson, ns + 'Postort')
            agd_tekniskKontaktperson_agd_postort.text = avsandare_dict.get('tk_city', '')

            agd_skapad = etree.SubElement(agd_avsandare, ns + 'Skapad')
            agd_skapad.text = fields.Datetime.now().replace(' ', 'T')
            agd_blankettgemensamt = etree.SubElement(skatteverket, ns + 'Blankettgemensamt')
            agd_arbetsgivare = etree.SubElement(agd_blankettgemensamt, ns + 'Arbetsgivare')
            agd_agregistreradid = etree.SubElement(agd_arbetsgivare, ns + 'AgRegistreradId')
            agd_agregistreradid.text = company_registry
            arbetsgivarekontaktperson = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.ag_contact')
            if not arbetsgivarekontaktperson:
                raise Warning(_(u'Please configurate arbetsgivare kontaktperson'))
            for ak in self.env['res.partner'].browse(eval(arbetsgivarekontaktperson)):
                agd_kontaktperson = etree.SubElement(agd_arbetsgivare, ns + 'Kontaktperson')
                agd_kontaktperson_agd_name = etree.SubElement(agd_kontaktperson, ns + 'Namn')
                agd_kontaktperson_agd_name.text = ak.name
                agd_kontaktperson_agd_telefon = etree.SubElement(agd_kontaktperson, ns + 'Telefon')
                agd_kontaktperson_agd_telefon.text = ak.phone or ak.mobile or ''
                agd_kontaktperson_agd_epostadress = etree.SubElement(agd_kontaktperson, ns + 'Epostadress')
                agd_kontaktperson_agd_epostadress.text = ak.email or ''
                if not ak.function:
                    raise Warning(_('Please fill the function for partner: %s') % ak.name)
                agd_kontaktperson_agd_sakomrade = etree.SubElement(agd_kontaktperson, ns + 'Sakomrade')
                agd_kontaktperson_agd_sakomrade.text = ak.function

            # Uppgift 1 HU
            period = self.period_start.date_start[:4] + self.period_start.date_start[5:7]
            hu_blankett = etree.SubElement(skatteverket, ns + 'Blankett')
            hu_arendeinformation = etree.SubElement(hu_blankett, ns + 'Arendeinformation')
            hu_arendeagare = etree.SubElement(hu_arendeinformation, ns + 'Arendeagare')
            hu_arendeagare.text = company_registry
            hu_priod = etree.SubElement(hu_arendeinformation, ns + 'Period')
            hu_priod.text = period
            hu_blankettinnehall = etree.SubElement(hu_blankett, ns + 'Blankettinnehall')
            hu_hu = etree.SubElement(hu_blankettinnehall, ns + 'HU')
            hu_arbetsgivarehugroup = etree.SubElement(hu_hu, ns + 'ArbetsgivareHUGROUP')
            hu_agregistreradid = etree.SubElement(hu_arbetsgivarehugroup, ns + 'AgRegistreradId')
            hu_agregistreradid.set('faltkod', '201')
            hu_agregistreradid.text = company_registry
            hu_redovisningsperiod = etree.SubElement(hu_hu, ns + 'RedovisningsPeriod')
            hu_redovisningsperiod.set('faltkod', '006')
            hu_redovisningsperiod.text = period
            hu_summaarbavgslf = etree.SubElement(hu_hu, ns + 'SummaArbAvgSlf')
            hu_summaarbavgslf.set('faltkod', TAGS_NEW.get('SummaArbAvgSlf'))
            hu_summaarbavgslf.text = get_tax_value('SumAvgBetala')
            hu_summaskatteavdr = etree.SubElement(hu_hu, ns + 'SummaSkatteavdr')
            hu_summaskatteavdr.set('faltkod', TAGS_NEW.get('SummaSkatteavdr'))
            hu_summaskatteavdr.text = get_tax_value('SumSkAvdr')

            # Uppgift IU
            seq = 1
            for slip in self.payslip_ids:
                iu_blankett = etree.SubElement(skatteverket, ns + 'Blankett')
                iu_arendeinformation = etree.SubElement(iu_blankett, ns + 'Arendeinformation')
                iu_arendeagare = etree.SubElement(iu_arendeinformation, ns + 'Arendeagare')
                iu_arendeagare.text = company_registry
                iu_priod = etree.SubElement(iu_arendeinformation, ns + 'Period')
                iu_priod.text = period
                iu_blankettinnehall = etree.SubElement(iu_blankett, ns + 'Blankettinnehall')
                iu_iu = etree.SubElement(iu_blankettinnehall, ns + 'IU')
                iu_arbetsgivareiugroup = etree.SubElement(iu_iu, ns + 'ArbetsgivareIUGROUP')
                iu_agregistreradid = etree.SubElement(iu_arbetsgivareiugroup, ns + 'AgRegistreradId')
                iu_agregistreradid.set('faltkod', '201')
                iu_agregistreradid.text = company_registry
                iu_betalningsmottagareiugroup = etree.SubElement(iu_iu, ns + 'BetalningsmottagareIUGROUP')
                iu_betalningsmottagareidinvoice = etree.SubElement(iu_betalningsmottagareiugroup, ns + 'BetalningsmottagareIDChoice')
                iu_betalningsmottagarid = etree.SubElement(iu_betalningsmottagareidinvoice, ns + 'BetalningsmottagarId')
                iu_betalningsmottagarid.set('faltkod', '215')
                iu_betalningsmottagarid.text = ''
                if slip.contract_id and slip.contract_id.employee_id.identification_id:
                    iu_betalningsmottagarid.text = slip.contract_id.employee_id.identification_id.replace('-', '')
                iu_redovisningsperiod = etree.SubElement(iu_iu, ns + 'RedovisningsPeriod')
                iu_redovisningsperiod.set('faltkod', '006')
                iu_redovisningsperiod.text = period
                iu_specifikationsnummer = etree.SubElement(iu_iu, ns + 'Specifikationsnummer')
                iu_specifikationsnummer.set('faltkod', '570')
                iu_specifikationsnummer.text = str(seq).zfill(3)
                seq += 1
                iu_kontantersattningulagag = etree.SubElement(iu_iu, ns + 'KontantErsattningUlagAG')
                iu_kontantersattningulagag.set('faltkod', '011')
                iu_kontantersattningulagag.text = ''
                bl = slip.line_ids.filtered(lambda l: l.code == 'bl')
                if bl:
                    iu_kontantersattningulagag.text = str(int(round(sum(bl.mapped('total')))))
                iu_avdrprelskatt = etree.SubElement(iu_iu, ns + 'AvdrPrelSkatt')
                iu_avdrprelskatt.set('faltkod', '001')
                iu_avdrprelskatt.text = ''
                prej = slip.line_ids.filtered(lambda l: l.code == 'prej')
                if prej:
                    iu_avdrprelskatt.text = str(int(round(sum(prej.mapped('total')))))
                resmil = slip.line_ids.filtered(lambda l: l.code == 'resmil')
                if resmil:
                    iu_bilersattning = etree.SubElement(iu_iu, ns + 'Bilersattning')
                    iu_bilersattning.set('faltkod', '050')
                    iu_bilersattning.text = '1'
                # ~ nettil = str(int(round(sum(slip.line_ids.with_context(nettil=self.env.ref('l10n_se_hr_payroll.hr_salary_rule_category-NETTIL')).filtered(lambda l: l.category_id == l._context.get('nettil')).mapped('total')))))
                # ~ if nettil > 0:
                    # ~ iu_kontantersattningejulagsa = etree.SubElement(iu_iu, ns + 'KontantErsattningEjUlagSA')
                    # ~ iu_kontantersattningejulagsa.set('faltkod', '131')
                    # ~ iu_kontantersattningejulagsa.text = nettil
            return skatteverket

        def schema_validate(xml):
            # Läs in schema. Skatteverkets är extra kinkig för att den är två
            # dokument (en import av arbetsgivardeklaration_component_1.1.xsd är
            # angiven i arbetsgivardeklaration_1.1.xsd).
            # Troligtvis kan vi lägga upp filerna lokalt i stället, så slipper vi
            # hämta dem från skatteverket.se varje gång.
            schema_root = etree.parse('http://xmls.skatteverket.se/se/skatteverket/da/arbetsgivardeklaration/arbetsgivardeklaration_1.1.xsd', base_url='http://xmls.skatteverket.se/se/skatteverket/da/arbetsgivardeklaration/')
            schema = etree.XMLSchema(schema_root)

            # ~ # Validera ett dokument som du skapat
            # ~ root = etree.Element('<foobar><foo>bar</foo></foobr>')
            # ~ schema.validate(root) # True eller False

            # ~ # Validera dokument vid inläsning från en sträng
            parser = etree.XMLParser(schema = schema)
            etree.fromstring(xml, parser)
            # ~ try:
                # ~ root = etree.fromstring(doc_str, parser)
                # ~ # Om du kommer hit så gick det bra
            # ~ except:
                # ~ # Dokumentet validerade ej

        xml = parse_xml(tax_account)
        # ~ xml = etree.tostring(xml, pretty_print=True, encoding="UTF-8", standalone=False)
        xml = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + etree.tostring(xml, pretty_print=True, encoding="UTF-8")
        schema_validate(xml)
        self.eskd_file = base64.b64encode(xml)

        ##
        #### Create move
        ##

        #TODO check all warnings
        tax_accounts = self.env['account.tax'].with_context({'period_id': self.period_start.id, 'state': self.target_move}).search([('name', '=', 'AgAvgPreS')])
        kontoskatte = self.env['account.account'].with_context({'period_from': self.period_start.id, 'period_to': self.period_start.id}).search([('id', 'in', self.env['account.financial.report'].search([('tax_ids', 'in', tax_accounts.mapped('children_tax_ids').mapped('id'))]).mapped('account_ids').mapped('id'))])
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
                    'period_id': self.period_start.id,
                    'date': fields.Date.today(),
                    'ref': u'Arbetsgivardeklaration',
                })
                if entry:
                    move_line_list = []
                    for k in kontoskatte:
                        credit = k.with_context(ctx).sum_period()
                        if credit != 0.0:
                            move_line_list.append((0, 0, {
                                'name': k.name,
                                'account_id': k.id,
                                'debit': int(round(abs(credit))),
                                'credit': 0.0,
                                'move_id': entry.id,
                            }))
                            total += credit
                    move_line_list.append((0, 0, {
                        'name': skattekonto.name,
                        'account_id': skattekonto.id,
                        'partner_id': self.env.ref('base.res_partner-SKV').id,
                        'debit': 0.0,
                        'credit': int(round(abs(total))),
                        'move_id': entry.id,
                    }))
                    entry.write({
                        'line_ids': move_line_list,
                    })
                    self.write({'move_id': entry.id})
            else:
                raise Warning(_('kontoskatte: %sst, skattekonto: %s') %(len(kontoskatte), skattekonto))

    @api.model
    def get_next_periods(self,length=1):
        last_declaration = self.search([],order='date_stop desc',limit=1)
        return self.env['account.period'].get_next_periods(last_declaration.period_start if last_declaration else None, 1)


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    periodic_compilation_id = fields.Many2one(comodel_name="account.periodic.compilation")
    @api.one
    @api.depends('total_amount')
    def _periodic_compilation(self):
        self.pc_supplied_goods = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
        self.pc_triangulation = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
        self.pc_services_supplied = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
    pc_supplied_goods = fields.Float(string='Supplied Goods',compute='_periodic_compilation',help="Value of supplies of goods")
    pc_triangulation  = fields.Float(string='Triangulation',compute='_periodic_compilation',help="Value of a triangulation")
    pc_services_supplied  = fields.Float(string='Services Supplied',compute='_periodic_compilation',help="Value of services supplied")
    pc_purchasers_vat = fields.Char(string="",relation='partner_id.vat')

# ~ class account_move(models.Model):
    # ~ _inherit = 'account.move'

    # ~ agd_declaration_id = fields.Many2one(comodel_name="account.agd.declaration")


# ~ class account_declaration_line(models.Model):
    # ~ _inherit = 'account.declaration.line'

    # ~ agd_declaration_id = fields.Many2one(comodel_name="account.agd.declaration")
