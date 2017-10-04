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

def mk_chart(data,type,year,accounts,rule):
    exid = 'chart_template_%s_%s' % (type,year)
    ke = record(data, exid, 'account.chart.template')
    field(ke, 'name', 'K2')
    field(ke, 'transfer_account_id', '', {'ref': 'chart1950'})
    field(ke, 'currency_id', '', {'ref': 'base.SEK'})
    field(ke, 'cash_account_code_prefix', '1910')
    field(ke, 'bank_account_code_prefix', '1930')
    field(ke, 'code_digits', '4')
    
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
@click.argument('input', type=click.File('rb'))
@click.argument('output', type=click.File('wb'))

def import_excel(year, input, output):
    wb = open_workbook(file_contents=input.read(), formatting_info=True)
    ws = wb.sheet_by_index(0)
    
    not_k2 = u'[Ej K2]'
    
    k2 = []
    k3 = []
    rule = Rule()
    
    for row in ws.get_rows():
        if type(row[2].value) == float and 1000 <= row[2].value <= 9999:
            k3.append({
                'code': str(int(row[2].value)),
                'name': row[3].value,
            })
            if row[1] != not_k2:
                k2.append({
                    'code': str(int(row[2].value)),
                    'name': row[3].value,
                })
        if type(row[5].value) == float and 1000 <= row[5].value <= 9999:
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
    
    root_account = record(data, 'chart1950', 'account.account.template')
    field(root_account,'name','Bank transfer')
    field(root_account,'code','1950')
    field(root_account,'user_type_id','',{'ref': 'account.data_account_type_current_assets'})
    field(root_account,'reconsile', '', {'eval': 'True'})

    trustee_type = record(data, 'trustee_assets', 'account.account.type')
    field(trustee_type,'name','Trustee Asset')
    field(trustee_type,'type','asset')
    field(trustee_type,'include_initial_balance','',{'eval': 'True'})
    untaxedreserve_type = record(data, 'untaxed_reserve', 'account.account.type')
    field(untaxedreserve_type,'name','Untaxed reserve')
    field(untaxedreserve_type,'type','asset')
    field(untaxedreserve_type,'include_initial_balance','',{'eval': 'True'})
    tax_type = record(data, 'tax', 'account.account.type')
    field(tax_type,'name','Tax in Balance sheet')
    field(tax_type,'type','asset')


    mk_chart(data,'K2',year,k2,rule)
    #~ mk_chart(data,'K3',year,k3,rule)

    # Write file.
    output.write(etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True))

if __name__ == '__main__':
    import_excel()
