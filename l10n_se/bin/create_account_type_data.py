# -*- coding: utf-8 -*-
import base64
import sys
import traceback
try:
    from xlrd import open_workbook
except ImportError:
    pass

xl_workbook = open_workbook('arsredovisning-2017-09-30.xlsx')

resultatrakning = xl_workbook.sheet_by_index(2)
balansrakning = xl_workbook.sheet_by_index(4)

r_element_name = 8
r_title = 10
# ~ r_saldo = 13
r_documentation = 16
r_account_type = 50
r_element_nix = []
r_main_type = [
    'RorelsensIntakterLagerforandringarMmAbstract',
    'RorelsekostnaderAbstract',
    'FinansiellaPosterAbstract',
    'BokslutsdispositionerAbstract',
    'SkatterAbstract',
]

b_element_name = 9
b_title = 11
# ~ b_saldo = 14
b_documentation = 17
b_account_type = 43
b_element_nix = [
    'ImmateriellaAnlaggningstillgangar',
    'MateriellaAnlaggningstillgangar',
    'FinansiellaAnlaggningstillgangar',
    'VarulagerMm',
    'KortfristigaFordringar',
    'KortfristigaPlaceringar',
    'ObeskattadeReserver',
    'LangfristigaSkulder',
    'KortfristigaSkulder',
]
b_main_type = [
    'TillgangarAbstract',
    'EgetKapitalSkulderAbstract',
]

r_lst = []
b_lst = []

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

def get_type(lst):
    if '1930' in lst:
        return 'liquidity'
    elif '2440' in lst:
        return 'payable'
    elif '1510' in lst:
        return 'receivable'
    else:
        return 'other'

def read_sheet(sheet=None, element_name=0, title=0, documentation=0, account_type=0, main_type=[] ,report_type='', nix=[], lst=None):
    mtype = ''
    for row in range(1, sheet.nrows):
        if sheet.cell(row, account_type).value == 'BFNAR':
            pass
            # ~ lst.append({
                # ~ 'name': sheet.cell(row, title).value,
                # ~ 'type': 'sum',
                # ~ 'element_name': sheet.cell(row, element_name).value,
                # ~ 'belong': sheet.cell(row, belong).value,
                # ~ 'data_type': sheet.cell(row, data_type).value,
                # ~ 'note': sheet.cell(row, documentation).value,
            # ~ })
        if sheet.cell(row, account_type).value == 'BFNAR' and sheet.cell(row, element_name).value in main_type:
            mtype = sheet.cell(row, element_name).value
        if sheet.cell(row, account_type).value == 'BAS-konto' and sheet.cell(row, element_name).value not in nix:
            if sheet.cell(row, element_name).value == 'OvrigaKortfristigaSkulder':
                account_type += 16
            domain = get_range_domain(get_account_range(sheet, account_type, row))
            lst.append({
                'name': sheet.cell(row, title).value,
                'type': get_type(domain[0][2]),
                'element_name': sheet.cell(row, element_name).value,
                'note': sheet.cell(row, documentation).value,
                'account_range': domain,
                'main_type': mtype,
                'report_type': report_type,
            })

read_sheet(resultatrakning, r_element_name, r_title, r_documentation, r_account_type, r_main_type, 'r', r_element_nix, r_lst)
read_sheet(balansrakning, b_element_name, b_title, b_documentation, b_account_type, b_main_type, 'b', b_element_nix, b_lst)

print """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
"""

for r in r_lst:
    print """        <record id="%s" model="account.account.type">
            <field name="name">%s</field>
            <field name="type">%s</field>
            <field name="element_name">%s</field>
            <field name="main_type">%s</field>
            <field name="report_type">%s</field>
            <field name="account_range">%s</field>
            <field name="note">%s</field>
        </record>
    """ %(r.get('element_name'), r.get('name'), r.get('type'), r.get('element_name'), r.get('main_type'), r.get('report_type'), r.get('account_range'), r.get('note'))

for b in b_lst:
    print """        <record id="%s" model="account.account.type">
            <field name="name">%s</field>
            <field name="type">%s</field>
            <field name="element_name">%s</field>
            <field name="main_type">%s</field>
            <field name="report_type">%s</field>
            <field name="account_range">%s</field>
            <field name="note">%s</field>
        </record>
    """ %(b.get('element_name'), b.get('name'), b.get('type'), b.get('element_name'), b.get('main_type'), b.get('report_type'), b.get('account_range'), b.get('note'))

print """    </data>
</odoo>
"""
