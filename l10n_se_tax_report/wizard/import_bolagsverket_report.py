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

    @api.model
    def get_account_financial_report_values(self, workbook):
        resultatrakning = workbook.sheet_by_index(2)
        balansrakning = workbook.sheet_by_index(4)

        r_element_name = 8
        r_title = 10
        r_sign = 11
        r_credit_debit = 13
        r_account_type = 50
        # sum rows
        r_sum = [
            'RorelseintakterLagerforandringarMm',
            'Rorelsekostnader',
            'FinansiellaPoster',
            'Bokslutsdispositioner',
        ]
        # all rows without accounts
        r_parents = {
            'RorelseresultatAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
            'RorelsensIntakterLagerforandringarMmAbstract': 'RorelseresultatAbstract',
            'RorelseintakterLagerforandringarMm': 'RorelsensIntakterLagerforandringarMmAbstract',
            'RorelsekostnaderAbstract': 'RorelseresultatAbstract',
            'Rorelsekostnader': 'RorelsekostnaderAbstract',
            'Rorelseresultat': 'ResultatrakningKostnadsslagsindeladAbstract',
            'FinansiellaPosterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
            'FinansiellaPoster': 'FinansiellaPosterAbstract',
            'ResultatEfterFinansiellaPoster': 'ResultatrakningKostnadsslagsindeladAbstract',
            'BokslutsdispositionerAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
            'Bokslutsdispositioner': 'BokslutsdispositionerAbstract',
            'ResultatForeSkatt': 'ResultatrakningKostnadsslagsindeladAbstract',
            'SkatterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
            'AretsResultat': 'ResultatrakningKostnadsslagsindeladAbstract',
        }

        b_element_name = 9
        b_title = 11
        b_sign = 12
        b_credit_debit = 14
        b_account_type = 43
        # sum rows
        b_sum = [
            'ImmateriellaAnlaggningstillgangar',
            'MateriellaAnlaggningstillgangar',
            'FinansiellaAnlaggningstillgangar',
            'VarulagerMm',
            'KortfristigaFordringar',
            'KortfristigaPlaceringar',
            'KassaBank',
            'BundetEgetKapital',
            'FrittEgetKapital',
            'ObeskattadeReserver',
            'Avsattningar',
            'LangfristigaSkulder',
            'KortfristigaSkulder',
        ]

        b_parents = {
            'TillgangarAbstract': 'BalansrakningAbstract',
            'TecknatEjInbetaltKapital': 'TillgangarAbstract',
            'AnlaggningstillgangarAbstract': 'TillgangarAbstract',
            'Tillgangar': 'TillgangarAbstract',
            'ImmateriellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
            'ImmateriellaAnlaggningstillgangar': 'ImmateriellaAnlaggningstillgangarAbstract',
            'MateriellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
            'MateriellaAnlaggningstillgangar': 'MateriellaAnlaggningstillgangarAbstract',
            'FinansiellaAnlaggningstillgangarAbstract': 'Anlaggningstillgangar',
            'FinansiellaAnlaggningstillgangar': 'FinansiellaAnlaggningstillgangarAbstract',
            'Anlaggningstillgangar': 'AnlaggningstillgangarAbstract',
            'OmsattningstillgangarAbstract': 'Tillgangar',
            'VarulagerMmAbstract': 'Omsattningstillgangar',
            'VarulagerMm': 'VarulagerMmAbstract',
            'KortfristigaFordringarAbstract': 'Omsattningstillgangar',
            'KortfristigaFordringar': 'KortfristigaFordringarAbstract',
            'KortfristigaPlaceringarAbstract': 'Omsattningstillgangar',
            'KortfristigaPlaceringar': 'KortfristigaPlaceringarAbstract',
            'KassaBankAbstract': 'Omsattningstillgangar',
            'KassaBank': 'KassaBankAbstract',
            'Omsattningstillgangar': 'Omsattningstillgangar',
            'EgetKapitalSkulderAbstract': 'BalansrakningAbstract',
            'EgetKapitalSkulder': 'EgetKapitalSkulderAbstract',
            'EgetKapitalAbstract': 'EgetKapitalSkulder',
            'EgetKapital': 'EgetKapitalAbstract',
            'BundetEgetKapitalAbstract': 'EgetKapitalAbstract',
            'BundetEgetKapital': 'BundetEgetKapitalAbstract',
            'FrittEgetKapitalAbstract': 'EgetKapitalAbstract',
            'FrittEgetKapital': 'FrittEgetKapitalAbstract',
            'ObeskattadeReserverAbstract': 'EgetKapitalSkulderAbstract',
            'ObeskattadeReserver': 'ObeskattadeReserverAbstract',
            'AvsattningarAbstract': 'EgetKapitalSkulderAbstract',
            'Avsattningar': 'AvsattningarAbstract',
            'LangfristigaSkulderAbstract': 'EgetKapitalSkulderAbstract',
            'LangfristigaSkulder': 'LangfristigaSkulderAbstract',
            'KortfristigaSkulderAbstract': 'EgetKapitalSkulderAbstract',
            'KortfristigaSkulder': 'KortfristigaSkulderAbstract',
        }

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

        r_lst = []
        b_lst = []

        parent = ''
        def read_sheet(sheet=None, element_name=0, title=0, account_type=0, parents={}, credit_debit=1, lst=None):
            for row in range(1, sheet.nrows):
                if sheet.cell(row, account_type).value == 'BFNAR' or sheet.cell(row, account_type).value == '':
                    lst.append({
                        'name': sheet.cell(row, title).value,
                        'type': 'sum',
                        'element_name': sheet.cell(row, element_name).value,
                        'parent_id': "[('element_name', '=', '%s')]" %(parents.get(sheet.cell(row, element_name).value) if parents.get(sheet.cell(row, element_name).value) else ''),
                        'sign': '-1' if find_sign(sheet, row, account_type, credit_debit) == 'credit' else '1',
                    })
                    parent = sheet.cell(row, element_name).value
                if sheet.cell(row, account_type).value == 'BAS-konto':
                    account = account_type
                    if sheet.cell(row, element_name).value == 'OvrigaKortfristigaSkulder':
                        account += 16
                    domain = get_range_domain(get_account_range(sheet, account, row))
                    lst.append({
                        'name': sheet.cell(row, title).value,
                        'type': 'accounts',
                        'element_name': sheet.cell(row, element_name).value,
                        'parent_id': "[('element_name', '=', '%s')]" %(parent if not parents.get(sheet.cell(row, element_name).value) else parents.get(sheet.cell(row, element_name).value)),
                        'sign': '-1' if sheet.cell(row, credit_debit).value == 'credit' else '1',
                        'account_ids': get_range_domain(get_account_range(sheet, account, row)),
                    })

        read_sheet(resultatrakning, r_element_name, r_title, r_account_type, r_parents, r_credit_debit, r_lst)
        read_sheet(balansrakning, b_element_name, b_title, b_account_type, b_parents, b_credit_debit, b_lst)

        return {'r_lst': r_lst, 'b_lst': b_lst}

    @api.model
    def create__update_financial_report(self, lst):
        for line in lst:
            financial_report = self.env['account.financial.report'].search([('element_name', '=', line.get('element_name'))])
            if financial_report:
                financial_report.write({
                    'name': line.get('name'),
                    'type': line.get('type'),
                    'parent_id': self.env['account.financial.report'].search(eval(line.get('parent_id'))).id,
                    'sign': eval(line.get('sign')),
                    'account_ids': [(6, 0, self.env['account.account'].search(line.get('account_ids')).mapped('id'))],
                    'sequence': 1,
                    'style_overwrite': 4 if line.get('account_ids') else 2,
                })
            else:
                self.env['account.financial.report'].create({
                    'name': line.get('name'),
                    'element_name': line.get('element_name'),
                    'type': line.get('type'),
                    'parent_id': self.env['account.financial.report'].search(eval(line.get('parent_id'))).id,
                    'sign': eval(line.get('sign')),
                    'account_ids': [(6, 0, self.env['account.account'].search(line.get('account_ids')).mapped('id'))],
                    'sequence': 1,
                    'style_overwrite': 4 if line.get('account_ids') else 2,
                })

    @api.multi
    def send_form(self):
        with TemporaryFile('w+') as fileobj:
            fileobj.write(base64.decodestring(self.data))
            fileobj.seek(0)
            workbook = open_workbook(file_contents=fileobj.read())
            lst = self.get_account_financial_report_values(workbook)
            r_list = lst.get('r_lst')
            b_list = lst.get('b_lst')
            self.create__update_financial_report(r_list)
            self.create__update_financial_report(b_list)
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
