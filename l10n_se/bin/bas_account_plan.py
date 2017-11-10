#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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

import base64
import sys
sys.path.append('./')
sys.path.append('../')
import traceback
from lxml import etree

import click
from xlrd import open_workbook
from account_rules import account_rules as Rule


def record(parent, id, model):
    r = etree.SubElement(parent, 'record')
    r.set('id', id)
    r.set('model', model)
    return r

def field(parent, name, value='', attrs=None):
    f = etree.SubElement(parent, 'field')
    f.set('name', name)
    if value:
        f.text = value
    for attr in attrs or {}:
        f.set(attr, attrs[attr] or 'None')
    return f

def mk_chart(data,type,name,year,accounts,rule):

    #~ root_account = record(data, '%s_1955_%s' % (type,year), 'account.account.template')
    #~ field(root_account,'name','Bank transfer')
    #~ field(root_account,'code','1955')
    #~ field(root_account,'user_type_id','',{'ref': 'account.data_account_type_current_assets'})
    #~ field(root_account,'reconcile', '', {'eval': 'True'})

    exid = 'chart_template_%s_%s' % (type,year)
    ke = record(data, exid, 'account.chart.template')
    field(ke, 'name', name)
    field(ke, 'parent_id', '', {'ref': 'chart_template_general'})
    field(ke, 'transfer_account_id', '', {'ref': 'chart1955'})
    #~ field(ke, 'transfer_account_id', '', {'ref': '%s_1955_%s' % (type,year)})
    field(ke, 'currency_id', '', {'ref': 'base.SEK'})
    field(ke, 'cash_account_code_prefix', '191')
    field(ke, 'bank_account_code_prefix', '193')
    field(ke, 'code_digits', '4')

    #~ root_account2 = record(data, '%s_1955_%s' % (type,year), 'account.account.template')
    #~ field(root_account2, 'chart_template_id', '', {'ref': exid})

    for account in accounts:
        r = record(data, '%s_%s_%s' % (type,account['code'], year), 'account.account.template')
        field(r, 'name', account['name'])
        field(r, 'code', account['code'])
        field(r, 'user_type_id', '', {'ref': rule.code2user_type_id(account['code'])})
        field(r, 'chart_template_id', '', {'ref': exid})
        if rule.code2note(account['code']):
            field(r, 'note', rule.code2note(account['code']))
        if rule.code2tax_ids(account['code']):
            field(r, 'tax_ids', '', {'eval': rule.code2tax_ids(account['code'])})
        if rule.code2tag_ids(account['code']):
            field(r, 'tag_ids', '', {'eval': rule.code2tag_ids(account['code'])})
        if rule.code2reconcile(account['code']):
            field(r, 'reconcile', '', {'eval': 'True'})

@click.command()
@click.option('--year', default=2017, help='Year for the Chart of Account.')
@click.argument('input', default='BAS-2017-kontotabell.xls',type=click.File('rb'))
@click.argument('output',default='../data/account_chart_template_k23.xml' ,type=click.File('wb'))

def import_excel(year, input, output):
    wb = open_workbook(file_contents=input.read(), formatting_info=True)
    ws = wb.sheet_by_index(0)

    not_k2 = u'[Ej K2]'

    k2 = []
    k3 = []
    rule = Rule()

    general_accounts = [1410,1510,1630,1650,1910,1920,1930,1955,2440,2610,2611,
                        2612,2613,2614,2615,2616,2618,2620,2621,2622,2623,2624,
                        2625,2626,2628,2630,2631,2632,2633,2634,2635,2636,2638,2640,
                        2641,2642,2643,2644,2645,2646,2647,2648,2649,2650,2660,
                        2710,2730,2760,2850,3000,3001,3002,3003,3004,3740,4000,
                        7000,7500,8990,8999]
    for row in ws.get_rows():
        if type(row[2].value) == float and 1000 <= row[2].value <= 9999 and not row[2].value in general_accounts:
            k3.append({
                'code': str(int(row[2].value)),
                'name': row[3].value,
            })
            if row[1] != not_k2:
                k2.append({
                    'code': str(int(row[2].value)),
                    'name': row[3].value,
                })
        if type(row[5].value) == float and 1000 <= row[5].value <= 9999 and not row[5].value in general_accounts:
            k3.append({
                'code': str(int(row[5].value)),
                'name': row[6].value,
            })
            if row[4] != not_k2:
                k2.append({
                    'code': str(int(row[5].value)),
                    'name': row[6].value,
                })

    root = etree.Element('odoo')
    data = etree.SubElement(root, 'data')

    mk_chart(data,'K1',u'K1 - Mindre verksamheter',year,k2,rule)
    mk_chart(data,'K2',u'K2 - Små till medelstora verksamheter',year,k2,rule)
    mk_chart(data,'K3',u'K3 - Medelstora till större verksamheter',year,k3,rule)
    mk_chart(data,'K4',u'K4 - större verksamheter / publika företag',year,k3,rule)

    # Write file.
    output.write(etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True))

if __name__ == '__main__':
    import_excel()
