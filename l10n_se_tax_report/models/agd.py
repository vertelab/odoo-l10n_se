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
    # ~ 'UlagSkLonSarsk',   #61:  sapx Särskild löneskatt för 81 år eller äldre
    # ~ 'SkLonSarsk',       #62: (sapx)6,15% av #61
    # ~ 'UlagAvgAmbassad',  #65: Ambassader och företag utan fast driftställe i Sverige samt särskild löneskatt på vissa försäkringar m.m.
    # ~ 'AvgAmbassad',      #66: Se uträkningsruta
    # ~ 'KodAmerika',       #67: Kod USA, Kanada, Québec m.fl.
    # ~ 'UlagAvgAmerika',   #69:
    # ~ 'AvgAmerika',       #70: Se uträkningsruta
    'UlagStodForetag',  #73: Forskning och utveckling
    'AvdrStodForetag',  #74: Avdrag 10%, dock högst 230000 kr
    'UlagStodUtvidgat', #75: Regionalt stöd för vissa branscher i stödområde
    'AvdrStodUtvidgat', #76: Avdrag 10%, dock högst 7100 kr
    'SumAvgBetala',     #78: Summa arbetsgivaravgifter
    'UlagSkAvdrLon',    #81: Lön och förmåner inkl. SINK
    'SkAvdrLon',        #82: Från lön och förmåner
    # ~ 'UlagSkAvdrPension',#83: Pension, livränta, försäkringsersättning inkl. SINK
    # ~ 'SkAvdrPension',    #84: Från pension m.m.
    # ~ 'UlagSkAvdrRanta',  #85: Ränta och utdelning
    # ~ 'SkAvdrRanta',      #86: Från ränta och utdelning
    'UlagSumSkAvdr',    #87: Summa underlag för skatteanvdrag
    'SumSkAvdr',        #88: Summa avdragen skatt
    # ~ 'SjukLonKostnEhs'   #99: Summa arbetsgivaravgifter och avdragen skatt att betala
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

class account_agd_declaration(models.Model):
    _name = 'account.agd.declaration'
    _inherits = {'account.declaration.line.id': 'line_id'}
    _inherit = 'account.declaration'
    _report_name = 'Agd'
    _order = 'date desc'

    line_id = fields.Many2one('account.declaration.line.id', auto_join=True, index=True, ondelete="cascade", required=True)
    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,default=_period_start)
    # ~ period_stop = fields.Many2one(comodel_name='account.period', string='Slut period',default=_period_stop)
    move_ids = fields.One2many(comodel_name='account.move',inverse_name="agd_declaration_id")
    line_ids = fields.One2many(comodel_name='account.declaration.line',inverse_name="agd_declaration_id")
    payslip_ids = fields.Many2many(comodel_name='hr.payslip', string='Payslips', compute='_payslip_ids')
    
    # ~ ADDITIONS
    generated_mis_report_id = fields.Many2one(comodel_name='mis.report.instance', string='mis_report_instance', ondelete='cascade', readonly = 'true')
    find_moves_by_period = fields.Boolean(
    default=False,string="Find Move Based On Period",
    help="A little confusing but vouchers/invoices has dates and which period they belong to. By default the mis report finds moves based on date. If this is checked then we find them based on period"
    )
    
    def  show_mis_report(self):
        self.ensure_one()
        return self.generated_mis_report_id.preview()

    @api.depends('period_start', 'period_stop', 'target_move','name','find_moves_by_period','accounting_method','accounting_yearend')
    def _vat(self):
         for decl in self:
             decl.SumSkAvdr = 0
             decl.SumAvgBetala = 0
             decl.ag_betala  = 0
             if decl.period_start and decl.period_stop and decl.generated_mis_report_id:
                decl.generated_mis_report_id.write({'find_moves_by_period': decl.find_moves_by_period})
                decl.generated_mis_report_id.period_ids.write({'manual_date_from':decl.period_start.date_start})
                decl.generated_mis_report_id.period_ids.write({'manual_date_to':decl.period_stop.date_stop})
                decl.generated_mis_report_id.write({'target_move':decl.target_move})
                if decl.accounting_yearend:#Om det är bokslutsperiod så är det vara faktura metoden som används.
                        decl.generated_mis_report_id.write({'accounting_method':'invoice'})
                else:
                        decl.generated_mis_report_id.write({'accounting_method':decl.accounting_method})
                        
                matrix = decl.generated_mis_report_id._compute_matrix()
                vat_momsutg_list_names = ['MomsUtgHog','MomsUtgMedel','MomsUtgLag','MomsInkopUtgHog','MomsInkopUtgMedel','MomsInkopUtgLag','MomsImportUtgHog', 'MomsImportUtgMedel', 'MomsImportUtgLag']
                for row in matrix.iter_rows():
                    vals = [c.val for c in row.iter_cells()]
                    # ~ _logger.debug("jakmar name: {} val: {}".format(row.kpi.name,vals[0]))
                    # ~ _logger.info('jakmar name: {} value: {}'.format(row.kpi.name,vals[0]))
                    if row.kpi.name == 'SumSkAvdr':
                        decl.SumSkAvdr = vals[0]
                    if row.kpi.name == 'SumAvgBetala':
                        decl.SumAvgBetala = vals[0]
                self.ag_betala = self.SumAvgBetala + self.SumSkAvdr
                 

    SumSkAvdr  = fields.Float(compute='_vat', store=True)
    SumAvgBetala = fields.Float(compute='_vat', store=True)
    ag_betala  = fields.Float(compute='_vat', store=True)
    
    @api.model
    def create(self,values):
        record = super(account_agd_declaration, self).create(values)
        
        if record.accounting_yearend:
            accounting_method = 'invoice'
        else:
            accounting_method = record.accounting_method
            record.generated_mis_report_id = self._generate_mis_report(
            record.period_start.date_start, 
            record.period_start.date_stop, 
            record.target_move, 
            record.name, 
            accounting_method, 
            record.find_moves_by_period
        )
        
        return record
        
    @api.model
    def _generate_mis_report(self, start_date, stop_date, target_move_param, name_param,accounting_method_param, find_moves_by_period_param):
        report_instance = self.env["mis.report.instance"].create(
            dict(
                report_id = self.env.ref('l10n_se_mis.report_ad').id,
                company_id = self.env.ref("base.main_company").id,
                target_move = target_move_param,
                name = "MIS Report:" + name_param,
                accounting_method = accounting_method_param,
                find_moves_by_period = find_moves_by_period_param,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name = "p1",
                            mode = "fix",
                            manual_date_from = start_date,
                            manual_date_to = stop_date,
                        ),
                    )
                ],
            )
        )
        return report_instance
    # ~ ADDITIONS

    @api.depends('period_start')
    def _payslip_ids(self):
        slips = self.env['hr.payslip'].search([('move_id.period_id.id','=',self.period_start.id)])
        self.payslip_ids = slips.mapped('id')

        _logger.warn('jakob ***  payslip ')

        self.move_ids = []
        self.move_ids = slips.mapped('move_id')
        # ~ for move in slips.mapped('move_id'):
            # ~ move.write({"agd_declaration_id":self.id})
        # ~ _logger.info('AGD: %s %s' % (slips.mapped('id'),slips.mapped('move_id.id')))
        
    # ~ @api.multi
    def show_journal_entries(self):
        ctx = {
            'period_start': self.period_start.id,
            'period_stop': self.period_start.id,
            'accounting_yearend': self.accounting_yearend,
            'accounting_method': self.accounting_method,
            'target_move': self.target_move,
        }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action.update({
            'display_name': _('Verifikat'),
            'domain': [('id', 'in', self.move_ids.mapped('id'))],
            'context': ctx,
        })
        return action

    @api.onchange('period_start')
    def onchange_period_start(self):
        if self.period_start:
            self.accounting_yearend = (self.period_start == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            self.period_stop = self.period_start
            self.date = fields.Date.to_string(fields.Date.from_string(self.period_start.date_stop) + timedelta(days=12))
            self.name = '%s %s' % (self._report_name,self.env['account.period'].period2month(self.period_start,short=False))
            
     # ~ @api.multi
    def get_move_line_recordset(self, row_kpi_names):
        self.ensure_one()
        move_line_recordset = self.env['account.move.line']
        period_id = self.generated_mis_report_id.period_ids[0].id
        matrix = self.generated_mis_report_id._compute_matrix()
        for row in matrix.iter_rows():
            # ~ Just gather up all account.move.lines if list is empty.
            if(len(row_kpi_names) == 0 or row.kpi.name in row_kpi_names):
                for cell in row.iter_cells():
                        drilldown_arg = cell.drilldown_arg
                        res = self.generated_mis_report_id.drilldown(drilldown_arg)
                        move_line_recordset += self.env['account.move.line'].search(res['domain'])
        return move_line_recordset
        
    # ~ @api.multi
    def get_move_recordset_from_line_recordset(self,move_line_recordset):
        move_recordset = self.env['account.move']
        for line in move_line_recordset:
                move_recordset |= line.move_id
        return move_recordset

    # ~ @api.multi
    def show_SumSkAvdr(self):
        move_line_recordset = get_move_line_recordset(['SumSkAvdr'])
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
            'context': {},
        })
        return action
    # ~ @api.multi
    def show_SumAvgBetala(self):
        move_line_recordset = get_move_line_recordset(['SumAvgBetala'])
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
            'domain': [('id', 'in', move_line_recordset.mapped('id'))],
            'context': {},
        })
        return action

    # ~ @api.one
    def do_draft(self):
        for rec in self:
            super(account_agd_declaration, self).do_draft()
            rec.slip_ids = []
            for move in rec.move_ids:
                move.agd_declaration_id = None

    # ~ @api.one
    def do_cancel(self):
        for rec in self:
            super(account_agd_declaration, self).do_draft()
            for move in rec.move_ids:
                move.agd_declaration_id = None


    def calculate(self): # make a short cut to print financial report
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("Du kan inte beräkna i denna status, ändra till utkast")
            # ~ if rec.accounting_method == "cash" and not rec.accounting_yearend:
                # ~ slips = rec.env['hr.payslip'].search([('move_id.period_id.id','=',rec.period_start.id)])
            # ~ else:
                # ~ slips = rec.env['hr.payslip'].search([('move_id.date','=',rec.period_start.id)])
            slips = rec.env['hr.payslip'].search([('move_id.period_id.id','=',rec.period_start.id)])
            rec.payslip_ids = slips.mapped('id')
            rec.move_ids = []
            for move in rec.mapped('move_id'):
                move.agd_declaration_id = rec.id
            
            ctx = {
                'period_start': rec.period_start.id,
                'period_stop': rec.period_start.id,
                'accounting_yearend': rec.accounting_yearend,
                'accounting_method': rec.accounting_method,
                'target_move': rec.target_move,
                'nix_journal_ids': [rec.env.ref('l10n_se_tax_report.agd_journal').id] #FIXA
            }

            rec._vat()
            ##
            ####  Create report lines
            ##
            # ~ OLD WAY TO DISPLAY THE REPORT!!!!!!!!!!!!!!!!
            # ~ for row in TAGS:
                # ~ line = self.env.ref('l10n_se_tax_report.agd_report_%s' % row)
                # ~ if not line:
                    # ~ raise Warning(_('Report line missing %' % row))
                # ~ self.env['account.declaration.line'].create({
                    # ~ 'agd_declaration_id': self.id,
                    # ~ 'balance': int(abs(line.with_context(ctx).sum_tax_period() if line.tax_ids else sum([a.with_context(ctx).sum_period() for a in line.account_ids])) or 0.0),
                    # ~ 'name': line.name,
                    # ~ 'level': line.level,
                    # ~ 'move_line_ids': [(6,0,line.with_context(ctx).get_moveline_ids())],
                    # ~ })

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
            ### new version of agd from February 2019
            ### https://skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/tekniskbeskrivningochtesttjanst/tekniskbeskrivning114.4.2cf1b5cd163796a5c8ba79b.html

            tax_account = rec.env['account.tax'].search([('tax_group_id', '=', rec.env.ref('l10n_se.tax_group_hr').id), ('name', 'not in', ['eSKDUpload', 'Ag', 'AgBrutU', 'AgAvgU', 'AgAvgAv', 'AgAvg', 'AgAvd', 'AgAvdU', 'AgAvgPreS', 'AgPre', 'UlagVXLon', 'AvgVXLon'])])
            def parse_xml(recordsets):
                def get_tax_value(matrix,tax):
                    for row in matrix.iter_rows():
                        vals = [c.val for c in row.iter_cells()]
                        _logger.debug("jakmar tax_input: {}, name: {} val: {}".format(tax,row.kpi.name,vals[0]))
                        # ~ _logger.info('jakmar name: {} value: {}'.format(row.kpi.name,vals[0]))
                        if row.kpi.name == tax:
                            _logger.warning(f"TAX VALUE {vals[0]}")
                            return vals[0]
                                            
                namespaces = {
                    'agd': "http://xmls.skatteverket.se/se/skatteverket/da/komponent/schema/1.1",
                    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
                    None: "http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1",
                }
                ns = '{%s}' %namespaces['agd']
                # 2021-03-25 Om du får felmeddelande och kommer hit laddar du saker i fel ordning!
                # Gå till "Bolag" och fyll i Org nr och moms nr. :-)
                company_registry = '16' + rec.env.user.company_id.company_registry.replace('-', '')
                attrib={'{%s}schemaLocation' % namespaces['xsi']: "http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1 http://xmls.skatteverket.se/se/skatteverket/da/arbetsgivardeklaration/arbetsgivardeklaration_1.1.xsd", 'omrade': 'Arbetsgivardeklaration'}
                skatteverket = etree.Element('Skatteverket', attrib=attrib, nsmap=namespaces)
                avsandare = rec.env['ir.config_parameter'].get_param('l10n_se_tax_report.agd_avsandare')
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
                agd_skapad.text = str(fields.Datetime.now()).replace(' ', 'T')
                agd_blankettgemensamt = etree.SubElement(skatteverket, ns + 'Blankettgemensamt')
                agd_arbetsgivare = etree.SubElement(agd_blankettgemensamt, ns + 'Arbetsgivare')
                agd_agregistreradid = etree.SubElement(agd_arbetsgivare, ns + 'AgRegistreradId')
                agd_agregistreradid.text = company_registry
                arbetsgivarekontaktperson = rec.env.user.company_id.ag_contact
                # ~ arbetsgivarekontaktperson = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.ag_contact')
                if not arbetsgivarekontaktperson:
                    raise Warning(_(u'Please configurate arbetsgivare kontaktperson'))
                # ~ for ak in self.env['res.partner'].browse(eval(arbetsgivarekontaktperson)):
                for ak in arbetsgivarekontaktperson:
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
                period = str(self.period_start.date_start)[:4] + str(self.period_start.date_start)[5:7]
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
                hu_summaarbavgslf.text = str(get_tax_value(rec.generated_mis_report_id._compute_matrix(),'SumAvgBetala'))
                hu_summaskatteavdr = etree.SubElement(hu_hu, ns + 'SummaSkatteavdr')
                hu_summaskatteavdr.set('faltkod', TAGS_NEW.get('SummaSkatteavdr'))
                hu_summaskatteavdr.text = str(get_tax_value(rec.generated_mis_report_id._compute_matrix(),'SumSkAvdr'))

                # https://skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/tekniskbeskrivningochtesttjanst/tekniskbeskrivning119.4.7eada0316ed67d7282a791.html
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
                    if slip.contract_id and slip.contract_id.employee_id.identification_id:
                        iu_betalningsmottagarid.text = slip.contract_id.employee_id.identification_id.replace('-', '')
                    else:
                        iu_betalningsmottagarid.text = "NOT SET; UNABLE TO IDENTIFY,please set identification_id on the employe"
                    # ~ iu_betalningsmottagarid.text = slip.employee_id.identification_id
                    # ~ if slip.contract_id and slip.contract_id.employee_id.identification_id:
                        # ~ iu_betalningsmottagarid.text = slip.contract_id.employee_id.identification_id.replace('-', '')
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

                # ~ # Validera dokument vid inläsning från en sträng
                try:
                    parser = etree.XMLParser(schema = schema)
                    etree.fromstring(xml, parser)
                except etree.XMLSyntaxError as e:
                    self.message_post(body=e)
                    _logger.warning(f"agd {e}")
                    return False
                return True

            xml = parse_xml(tax_account)
            # ~ _logger.warning(f"AGD{xml}")
            _logger.warning('AGD XML !"¤!"#!¤"# %s' % etree.tostring(xml, pretty_print=True, encoding="UTF-8"))
            # ~ xml = etree.tostring(xml, pretty_print=True, encoding="UTF-8", standalone=False)
            xml = b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + (etree.tostring(xml, pretty_print=True, encoding="UTF-8",method="xml"))
            if not schema_validate(xml):
                pass
            self.eskd_file = base64.b64encode(xml)
            
            ##
            #### Create move
            ##
            # ~ LOOOK HERE!!!!!!!!!!!!!!!!!!E
            #TODO check all warnings
            #This method uses financial report to get base account
            
            tax_accounts = self.env['account.tax'].search([('name', 'in', ['SkAvdrLon', 'AvgHel'])])
            kontoskatte = tax_accounts.invoice_repartition_line_ids[1].mapped('account_id')
            _logger.warning('kontoskatte %s' % kontoskatte)
            
            # ~ agd_journal_id = self.env['ir.config_parameter'].get_param('l10n_se_tax_report.agd_journal')
            agd_journal_id = rec.env.user.company_id.agd_journal
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
                        for k in kontoskatte: #CHANGES NEEDED
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
                            'partner_id': self.env.ref('l10n_se.res_partner-SKV').id,
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
                    
            if self.state in ['draft']:
                self.state = 'confirmed'


    @api.model
    def get_next_periods(self,length=1):
        last_declaration = self.search([],order='date_stop desc',limit=1)
        return self.env['account.period'].get_next_periods(last_declaration.period_start if last_declaration else None, 1)


class account_move(models.Model):
    _inherit = 'account.move'

    agd_declaration_id = fields.Many2one(comodel_name="account.agd.declaration")


class account_declaration_line(models.Model):
    _inherit = 'account.declaration.line'

    agd_declaration_id = fields.Many2one(comodel_name="account.agd.declaration")




# ~ <Skatteverket xmlns:agd="http://xmls.skatteverket.se/se/skatteverket/da/komponent/schema/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1" xsi:schemaLocation="http://xmls.skatteverket.se/se/skatteverket/da/instans/schema/1.1 http://xmls.skatteverket.se/se/skatteverket/da/arbetsgivardeklaration/arbetsgivardeklaration_1.1.xsd" omrade="Arbetsgivardeklaration">  <agd:Avsandare>\n    <agd:Programnamn>Odoo 14.0</agd:Programnamn>    <agd:Organisationsnummer>165569363707</agd:Organisationsnummer>    <agd:TekniskKontaktperson>\n      <agd:Namn>Jakob Krabbe</agd:Namn>      <agd:Telefon>013-9919480</agd:Telefon>    <agd:Epostadress>support@vertel.se</agd:Epostadress>      <agd:Utdelningsadress1>Strandgatan 2</agd:Utdelningsadress1>     <agd:Postnummer>58226</agd:Postnummer>      <agd:Postort>Link\xc3\xb6ping</agd:Postort>    </agd:TekniskKontaktperson>    <agd:Skapad>2021-09-30T13:00:04</agd:Skapad>  </agd:Avsandare>  <agd:Blankettgemensamt>   <agd:Arbetsgivare>      <agd:AgRegistreradId>16SE123456789701</agd:AgRegistreradId>      <agd:Kontaktperson>        <agd:Namn>Joel Willis</agd:Namn>        <agd:Telefon>(683)-556-5104</agd:Telefon>       <agd:Epostadress>joel.willis63@example.com</agd:Epostadress>       <agd:Sakomrade>WHOO CARES LOL</agd:Sakomrade>     </agd:Kontaktperson>    </agd:Arbetsgivare> </agd:Blankettgemensamt> <agd:Blankett>    <agd:Arendeinformation>      <agd:Arendeagare>16SE123456789701</agd:Arendeagare>      <agd:Period>202101</agd:Period>   </agd:Arendeinformation>   <agd:Blankettinnehall>     <agd:HU>      <agd:ArbetsgivareHUGROUP>          <agd:AgRegistreradId faltkod="201">16SE123456789701</agd:AgRegistreradId>       </agd:ArbetsgivareHUGROUP>        <agd:RedovisningsPeriod faltkod="006">202101</agd:RedovisningsPeriod>        <agd:SummaArbAvgSlf faltkod="487"></agd:SummaArbAvgSlf>        <agd:SummaSkatteavdr faltkod="497"></agd:SummaSkatteavdr>      </agd:HU>    </agd:Blankettinnehall>  </agd:Blankett></Skatteverket>'
