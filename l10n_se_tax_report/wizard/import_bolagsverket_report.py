# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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
from odoo.exceptions import except_orm, Warning, RedirectWarning
from tempfile import TemporaryFile
import base64
import sys
import traceback
try:
    from xlrd import open_workbook
    import xml.etree.cElementTree as ET
    from xml.dom import minidom
except ImportError:
    _logger.info('project_task_planned_vehicle_import requires xlrd (pip install xlrd)')

import logging
_logger = logging.getLogger(__name__)

class ImportBolagsverketReports(models.TransientModel):
    _name = 'account.financial.report.bolagsverket.import'

    data = fields.Binary('File', required=True)
    file_name = fields.Char(string='File Name')
    xml_sheet = fields.Selection(string='Sheet', required=True, selection=[('simple', 'Simple'), ('complete', 'Complete')])

    # ~ @api.multi
    def get_workbook(self, data):
        with TemporaryFile('w+') as fileobj:
            fileobj.write(base64.decodestring(data))
            fileobj.seek(0)
            workbook = open_workbook(file_contents=fileobj.read())
            return workbook

    # ~ @api.multi
    def get_workbook_sheet_index(self, name):
        workbook = self.get_workbook(self.data)
        sheets = []
        for index in range(0, len(workbook.sheets())):
            if workbook.sheet_by_index(index).name == name:
                return index
        return 0

    @api.model
    def get_account_financial_report_values(self, workbook, file_name, sheet):

        def get_account_range(sheet, account_type, row):
            account_range = []
            col = account_type
            while (sheet.cell(row, col).value == 'BAS-konto'):
                account_range.append(sheet.cell(row, col+1).value)
                col += 8
            return account_range

        def get_range_domain(number_list):
            code_list = []
            for number in number_list:
                if 'x' in number:
                    if '-' in number:
                        code_list += [str(i) for i in range(int(number.split('-')[0].replace('x', '0')), int(number.split('-')[1].replace('x', '9'))+1)]
                    else:
                        code_list += [str(i) for i in range(int(number.replace('x', '0')), int(number.replace('x', '9'))+1)]
                else:
                    if '-' in number:
                        code_list += [str(i) for i in range(int(number.split('-')[0]), int(number.split('-')[1])+1)]
                    else:
                        code_list += [number]
            return [('code', 'in', code_list)]

        def find_sign(sheet=None, row=1, account_type=0, credit_debit=1):
            r = row
            while (sheet.cell(r, account_type).value != 'BAS-konto'):
                sign = sheet.cell(r, credit_debit).value
                r += 1
                if r == sheet.nrows:
                    break
            return sign

        parent = ''
        def read_sheet(sheet=None, element_name=0, title=0, account_type=0, parents={}, credit_debit=1, lst=None):
            for row in range(1, sheet.nrows):
                if sheet.cell(row, account_type).value == 'BFNAR' or sheet.cell(row, account_type).value == '':
                    lst.append({
                        'name': (sheet.cell(row, title).value + ' (' + file_name + ')') if row == 1 else sheet.cell(row, title).value,
                        'version_name': file_name,
                        'type': 'sum',
                        'element_name': sheet.cell(row, element_name).value,
                        'parent_id': "[('element_name', '=', '%s')]" %(parents.get(sheet.cell(row, element_name).value) if parents.get(sheet.cell(row, element_name).value) else ''),
                        'sign': '-1' if find_sign(sheet, row, account_type, credit_debit) == 'credit' else '1',
                        'sequence': 1,
                        'style_overwrite': 2,
                    })
                    parent = sheet.cell(row, element_name).value
                if sheet.cell(row, account_type).value == 'BAS-konto':
                    account = account_type
                    if sheet.cell(row, element_name).value == 'OvrigaKortfristigaSkulder':
                        account += 16
                    domain = get_range_domain(get_account_range(sheet, account, row))
                    lst.append({
                        'name': sheet.cell(row, title).value,
                        'version_name': file_name,
                        'type': 'accounts',
                        'element_name': sheet.cell(row, element_name).value,
                        'parent_id': "[('element_name', '=', '%s')]" %(parent if not parents.get(sheet.cell(row, element_name).value) else parents.get(sheet.cell(row, element_name).value)),
                        'sign': '-1' if sheet.cell(row, credit_debit).value == 'credit' else '1',
                        'sequence': 1,
                        'style_overwrite': 4,
                        'account_ids': get_range_domain(get_account_range(sheet, account, row)),
                    })

        def get_resultatrakning_list(mode):
            if mode == 'complete':
                r_element_name = 8
                r_title = 10
                r_sign = 11
                r_credit_debit = 13
                r_account_type = 50
                # all rows without accounts
                r_parents = {
                    'RorelseresultatAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'RorelsensIntakterLagerforandringarMmAbstract': 'RorelseresultatAbstract',
                    'RorelseintakterLagerforandringarMm': 'RorelsensIntakterLagerforandringarMmAbstract', # sum row
                    'RorelsekostnaderAbstract': 'RorelseresultatAbstract',
                    'Rorelsekostnader': 'RorelsekostnaderAbstract', # sum row
                    'Rorelseresultat': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'FinansiellaPosterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'FinansiellaPoster': 'FinansiellaPosterAbstract', # sum row
                    'ResultatEfterFinansiellaPoster': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'BokslutsdispositionerAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'Bokslutsdispositioner': 'BokslutsdispositionerAbstract', # sum row
                    'ResultatForeSkatt': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'SkatterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
                    'AretsResultat': 'ResultatrakningKostnadsslagsindeladAbstract',
                }
                resultatrakning = workbook.sheet_by_index(self.get_workbook_sheet_index(u'Resultaträkning'))
            else:
                r_element_name = 7
                r_title = 9
                r_sign = 10
                r_credit_debit = 12
                r_account_type = 41
                # all rows without accounts
                r_parents = {
                    'RorelseresultatAbstract': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'Rorelseresultat': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'FinansiellaPosterAbstract': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'FinansiellaPoster': 'FinansiellaPosterAbstract', # sum row
                    'ResultatEfterFinansiellaPoster': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'BokslutsdispositionerAbstract': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'Bokslutsdispositioner': 'BokslutsdispositionerAbstract', # sum row
                    'ResultatForeSkatt': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'SkatterAbstract': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                    'AretsResultat': 'ResultatrakningKostnadsslagsindeladForkortadAbstract',
                }
                resultatrakning = workbook.sheet_by_index(self.get_workbook_sheet_index(u'Förkortad resultaträkning'))
            r_lst = []
            read_sheet(resultatrakning, r_element_name, r_title, r_account_type, r_parents, r_credit_debit, r_lst)
            return r_lst

        def get_balansrakning_list(mode):
            b_element_name = 9
            b_title = 11
            b_sign = 12
            b_credit_debit = 14
            b_account_type = 43
            if mode == 'complete':
                # all rows without accounts
                b_parents = {
                    'TillgangarAbstract': 'BalansrakningAbstract',
                    'TecknatEjInbetaltKapital': 'TillgangarAbstract',
                    'AnlaggningstillgangarAbstract': 'TillgangarAbstract',
                    'Tillgangar': 'TillgangarAbstract',
                    'ImmateriellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
                    'ImmateriellaAnlaggningstillgangar': 'ImmateriellaAnlaggningstillgangarAbstract', # sum row
                    'MateriellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
                    'MateriellaAnlaggningstillgangar': 'MateriellaAnlaggningstillgangarAbstract', # sum row
                    'FinansiellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
                    'FinansiellaAnlaggningstillgangar': 'FinansiellaAnlaggningstillgangarAbstract', # sum row
                    'Anlaggningstillgangar': 'AnlaggningstillgangarAbstract',
                    'OmsattningstillgangarAbstract': 'TillgangarAbstract',
                    'VarulagerMmAbstract': 'Omsattningstillgangar',
                    'VarulagerMm': 'VarulagerMmAbstract', # sum row
                    'KortfristigaFordringarAbstract': 'Omsattningstillgangar',
                    'KortfristigaFordringar': 'KortfristigaFordringarAbstract', # sum row
                    'KortfristigaPlaceringarAbstract': 'Omsattningstillgangar',
                    'KortfristigaPlaceringar': 'KortfristigaPlaceringarAbstract', # sum row
                    'KassaBankAbstract': 'Omsattningstillgangar',
                    'KassaBank': 'KassaBankAbstract', # sum row
                    'Omsattningstillgangar': 'OmsattningstillgangarAbstract',
                    'EgetKapitalSkulderAbstract': 'BalansrakningAbstract',
                    'EgetKapitalSkulder': 'EgetKapitalSkulderAbstract',
                    'EgetKapitalAbstract': 'EgetKapitalSkulder',
                    'EgetKapital': 'EgetKapitalAbstract',
                    'BundetEgetKapitalAbstract': 'EgetKapitalAbstract',
                    'BundetEgetKapital': 'BundetEgetKapitalAbstract', # sum row
                    'FrittEgetKapitalAbstract': 'EgetKapitalAbstract',
                    'FrittEgetKapital': 'FrittEgetKapitalAbstract', # sum row
                    'ObeskattadeReserverAbstract': 'EgetKapitalSkulderAbstract',
                    'ObeskattadeReserver': 'ObeskattadeReserverAbstract', # sum row
                    'AvsattningarAbstract': 'EgetKapitalSkulderAbstract',
                    'Avsattningar': 'AvsattningarAbstract', # sum row
                    'LangfristigaSkulderAbstract': 'EgetKapitalSkulderAbstract',
                    'LangfristigaSkulder': 'LangfristigaSkulderAbstract', # sum row
                    'KortfristigaSkulderAbstract': 'EgetKapitalSkulderAbstract',
                    'KortfristigaSkulder': 'KortfristigaSkulderAbstract', # sum row
                }
                balansrakning = workbook.sheet_by_index(self.get_workbook_sheet_index(u'Balansräkning'))
            else:
                # all rows without accounts
                b_parents = {
                    'TillgangarAbstract': 'BalansrakningForkortadAbstract',
                    'Tillgangar': 'TillgangarAbstract',
                    'EgetKapitalSkulderAbstract': 'BalansrakningForkortadAbstract',
                    'EgetKapitalSkulder': 'EgetKapitalSkulderAbstract',
                    'TecknatEjInbetaltKapital': 'TillgangarAbstract',
                    'AnlaggningstillgangarAbstract': 'TillgangarAbstract',
                    'Anlaggningstillgangar': 'AnlaggningstillgangarAbstract',
                    'OmsattningstillgangarAbstract': 'TillgangarAbstract',
                    'Omsattningstillgangar': 'OmsattningstillgangarAbstract',
                    'EgetKapitalAbstract': 'EgetKapitalSkulderAbstract',
                    'EgetKapital': 'EgetKapitalAbstract',
                    'ObeskattadeReserver': 'EgetKapitalSkulderAbstract',
                    'AvsattningarForkortad': 'EgetKapitalSkulderAbstract',
                    'AvsattningarPensionerLiknandeForpliktelserEnligtLag': 'EgetKapitalSkulderAbstract',
                    'LangfristigaSkulder': 'EgetKapitalSkulderAbstract', # sum row
                    'KortfristigaSkulder': 'EgetKapitalSkulderAbstract', # sum row
                    'BundetEgetKapitalAbstract': 'EgetKapitalAbstract',
                    'BundetEgetKapital': 'BundetEgetKapitalAbstract', # sum row
                    'FrittEgetKapitalAbstract': 'EgetKapitalAbstract',
                    'FrittEgetKapital': 'FrittEgetKapitalAbstract', # sum row
                }
                balansrakning = workbook.sheet_by_index(self.get_workbook_sheet_index(u'Förkortat balansräkning'))
            b_lst = []
            read_sheet(balansrakning, b_element_name, b_title, b_account_type, b_parents, b_credit_debit, b_lst)
            return b_lst

        sheet_list = []
        if sheet == 'complete':
            sheet_list += get_resultatrakning_list('complete')
            sheet_list += get_balansrakning_list('complete')
        else:
            sheet_list += get_resultatrakning_list('simple')
            sheet_list += get_balansrakning_list('simple')

        return sheet_list

    @api.model
    def create_update_financial_report(self, lst):
        for line in lst:
            financial_report = self.env['account.financial.report'].search([('element_name', '=', line.get('element_name'))])
            if financial_report:
                financial_report.write({
                    'name': line.get('name'),
                    'version_name': line.get('version_name'),
                    'type': line.get('type'),
                    'parent_id': self.env['account.financial.report'].search(eval(line.get('parent_id'))).id,
                    'sign': eval(line.get('sign')),
                    'account_ids': [(6, 0, self.env['account.account'].search(line.get('account_ids')).mapped('id'))],
                    'sequence': line.get('sequence'),
                    'style_overwrite': line.get('style_overwrite'),
                })
            else:
                self.env['account.financial.report'].create({
                    'name': line.get('name'),
                    'element_name': line.get('element_name'),
                    'version_name': line.get('version_name'),
                    'type': line.get('type'),
                    'parent_id': self.env['account.financial.report'].search(eval(line.get('parent_id'))).id,
                    'sign': eval(line.get('sign')),
                    'account_ids': [(6, 0, self.env['account.account'].search(line.get('account_ids')).mapped('id'))],
                    'sequence': line.get('sequence'),
                    'style_overwrite': line.get('style_overwrite'),
                })

    # ~ @api.multi
    def send_form(self):
        sheet = self.xml_sheet
        workbook = self.get_workbook(self.data)
        lst = self.get_account_financial_report_values(workbook, self.file_name, sheet)
        self.create_update_financial_report(lst)
        return {
            'name': _('Financial Report Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.financial.report',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_id': self.env.ref('account.action_account_financial_report_tree').id,
            'limit': 2000,
            'target': 'current',
        }
