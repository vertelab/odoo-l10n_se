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
    
    for account in k2:
        account['reconcile'] = rule.code2reconcile(account['code'])
        account['tax_ids'] = rule.code2tax_ids(account['code'])
        account['user_type_id'] = rule.code2user_type_id(account['code'])
        account['note'] = rule.code2note(account['code'])
        account['tag_ids'] = rule.code2tag_ids(account['code'])

    for account in k3:
        account['reconcile'] = rule.code2reconcile(account['code'])
        account['tax_ids'] = rule.code2tax_ids(account['code'])
        account['user_type_id'] = rule.code2user_type_id(account['code'])
        account['note'] = rule.code2note(account['code'])
        account['tag_ids'] = rule.code2tag_ids(account['code'])

    root = etree.Element('odoo')
    data = etree.SubElement(root, 'data')
    
    # K2
    k2_exid = 'chart_template_k2_%s' % year
    k2e = record(data, k2_exid, 'account.chart.template')
    field(k2e, 'name', 'K2')
    #~ field(k2e, 'transfer_account_id', '', {'ref': 'TODO!!!'})
    field(k2e, 'currency_id', '', {'ref': 'base.SEK'})
    for account in k2:
        r = record(data, 'k2_%s_%s' % (account['code'], year), 'account.account.template')
        field(r, 'name', account['name'])
        field(r, 'code', account['code'])
        field(r, 'user_type_id', '', {'ref': account['user_type_id']})
        field(r, 'chart_template_id', '', {'ref': k2_exid})
        if account['note']:
            field(r, 'note', account['note'])
        if account['tax_ids']:
            field(r, 'tax_ids', '', {'eval': account['tax_ids']})
        if account['tag_ids']:
            field(r, 'tag_ids', '', {'eval': account['tag_ids']})
        if account['reconcile']:
            field(r, 'reconcile', '', {'eval': 'True'})
    
    # K3
    k3_exid = 'chart_template_k3_%s' % year
    k3e = record(data, k3_exid, 'account.chart.template')
    field(k3e, 'name', 'k3')
    #~ field(k3e, 'transfer_account_id', '', {'ref': 'TODO!!!'})
    field(k3e, 'currency_id', '', {'ref': 'base.SEK'})
    for account in k3:
        r = record(data, 'k3_%s_%s' % (account['code'], year), 'account.account.template')
        field(r, 'name', account['name'])
        field(r, 'code', account['code'])
        field(r, 'user_type_id', '', {'ref': account['user_type_id']})
        field(r, 'chart_template_id', '', {'ref': k3_exid})
        if account['note']:
            field(r, 'note', account['note'])
        if account['tax_ids']:
            field(r, 'tax_ids', '', {'eval': account['tax_ids']})
        if account['tag_ids']:
            field(r, 'tag_ids', '', {'eval': account['tag_ids']})
        if account['reconcile']:
            field(r, 'reconcile', '', {'eval': 'True'})

    # Write file.
    output.write(etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True))

if __name__ == '__main__':
    import_excel()
