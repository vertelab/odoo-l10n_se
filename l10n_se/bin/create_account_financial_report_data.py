# -*- coding: utf-8 -*-
try:
    from xlrd import open_workbook
except ImportError:
    pass

xl_workbook = open_workbook('arsredovisning-2017-09-30.xlsx')

resultatrakning = xl_workbook.sheet_by_index(2)
balansrakning = xl_workbook.sheet_by_index(4)

r_element_name = 8
r_title = 10
r_credit_debit = 13
r_account_type = 50
# title rows
r_main_type = [
    'RorelsensIntakterLagerforandringarMmAbstract',
    'RorelsekostnaderAbstract',
    'FinansiellaPosterAbstract',
    'BokslutsdispositionerAbstract',
    'SkatterAbstract',
]
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
    'Rorelseresultat': 'ResultatrakningKostnadsslagsindeladAbstract',
    'FinansiellaPosterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
    'FinansiellaPoster': 'ResultatrakningKostnadsslagsindeladAbstract',
    'BokslutsdispositionerAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
    'Bokslutsdispositioner': 'ResultatrakningKostnadsslagsindeladAbstract',
    'ResultatForeSkatt': 'ResultatrakningKostnadsslagsindeladAbstract',
    'SkatterAbstract': 'ResultatrakningKostnadsslagsindeladAbstract',
    'AretsResultat': 'ResultatrakningKostnadsslagsindeladAbstract',
    'RorelsensIntakterLagerforandringarMmAbstract': 'RorelseresultatAbstract',
    'RorelseintakterLagerforandringarMm': 'RorelseresultatAbstract',
    'RorelsekostnaderAbstract': 'RorelseresultatAbstract',
    'Rorelsekostnader': 'RorelseresultatAbstract',
}

b_element_name = 9
b_title = 11
b_credit_debit = 14
b_account_type = 43
b_main_type = [
    'ImmateriellaAnlaggningstillgangarAbstract',
    'MateriellaAnlaggningstillgangarAbstract',
    'FinansiellaAnlaggningstillgangarAbstract',
    'OmsattningstillgangarAbstract',
    'KortfristigaFordringarAbstract',
    'KortfristigaPlaceringarAbstract',
    'KassaBankAbstract',
    'BundetEgetKapitalAbstract',
    'FrittEgetKapitalAbstract',
    'ObeskattadeReserverAbstract',
    'AvsattningarAbstract',
    'LangfristigaSkulderAbstract',
    'KortfristigaSkulderAbstract',
]
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

def find_sign(sheet=None, row, credit_debit):
    r = row
    sign = ''
    while (sheet.cell(row, account_type).value != 'BAS-konto'):
        sign = sheet.cell(r, credit_debit).value
        r += 1
    return sign

r_lst = []
b_lst = []

def read_sheet(sheet=None, element_name=0, title=0, documentation=0, account_type=0, main_type=[], parents={}, credit_debit, lst=None):
    for row in range(1, sheet.nrows):
        if sheet.cell(row, account_type).value == 'BFNAR':
            lst.append({
                'name': sheet.cell(row, title).value,
                'type': 'sum',
                'element_name': sheet.cell(row, element_name).value,
                'parent_id': "[('element_name', '=', %s)]" %parents.get(sheet.cell(row, element_name).value) if parents.get(sheet.cell(row, element_name).value) else None,
                'sign': '-1' if find_sign(sheet, row, credit_debit) == 'credit' else '1',
            })
            mtype = sheet.cell(row, element_name).value
        if sheet.cell(row, account_type).value == 'BAS-konto':
            if sheet.cell(row, element_name).value == 'OvrigaKortfristigaSkulder':
                account_type += 16
            domain = get_range_domain(get_account_range(sheet, account_type, row))
            lst.append({
                'name': sheet.cell(row, title).value,
                'accounts': 'sum',
                'element_name': sheet.cell(row, element_name).value,
                'parent_id': None, #TODO: find parents
                'sign': '-1' if sheet.cell(row, credit_debit).value == 'credit' else '1',
                'account_ids': get_range_domain(get_account_range(sheet, account_type, row)),
            })

read_sheet(resultatrakning, r_element_name, r_title, r_documentation, r_account_type, r_main_type, r_parents, r_credit_debit, r_lst)
# ~ read_sheet(balansrakning, b_element_name, b_title, b_documentation, b_account_type, b_main_type, b_element_nix, b_lst)

print """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
"""

# ~ for r in r_lst:
    # ~ print """        <record id="%s" model="account.account.type">
            # ~ <field name="name">%s</field>
            # ~ <field name="type">%s</field>
            # ~ <field name="element_name">%s</field>
            # ~ <field name="main_type">%s</field>
            # ~ <field name="report_type">%s</field>
            # ~ <field name="account_range">%s</field>
            # ~ <field name="note">%s</field>
        # ~ </record>
    # ~ """ %(r.get('element_name'), r.get('name'), r.get('type'), r.get('element_name'), r.get('main_type'), r.get('report_type'), r.get('account_range'), r.get('note'))

# ~ for b in b_lst:
    # ~ print """        <record id="%s" model="account.account.type">
            # ~ <field name="name">%s</field>
            # ~ <field name="type">%s</field>
            # ~ <field name="element_name">%s</field>
            # ~ <field name="main_type">%s</field>
            # ~ <field name="report_type">%s</field>
            # ~ <field name="account_range">%s</field>
            # ~ <field name="note">%s</field>
        # ~ </record>
    # ~ """ %(b.get('element_name'), b.get('name'), b.get('type'), b.get('element_name'), b.get('main_type'), b.get('report_type'), b.get('account_range'), b.get('note'))

print """    </data>
</odoo>
"""
