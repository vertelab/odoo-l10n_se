# -*- coding: utf-8 -*-
try:
    from xlrd import open_workbook
    import xml.etree.cElementTree as ET
    from xml.dom import minidom
except ImportError:
    pass

xl_workbook = open_workbook('arsredovisning-2017-09-30.xlsx')

resultatrakning = xl_workbook.sheet_by_index(2)
balansrakning = xl_workbook.sheet_by_index(4)

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
    'OmsattningstillgangarAbstract': 'TillgangarAbstract',
    'VarulagerMmAbstract': 'Omsattningstillgangar',
    'VarulagerMm': 'VarulagerMmAbstract',
    'KortfristigaFordringarAbstract': 'Omsattningstillgangar',
    'KortfristigaFordringar': 'KortfristigaFordringarAbstract',
    'KortfristigaPlaceringarAbstract': 'Omsattningstillgangar',
    'KortfristigaPlaceringar': 'KortfristigaPlaceringarAbstract',
    'KassaBankAbstract': 'Omsattningstillgangar',
    'KassaBank': 'KassaBankAbstract',
    'Omsattningstillgangar': 'OmsattningstillgangarAbstract',
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
                code_list += [i for i in range(int(number.split('-')[0].replace('x', '0')), int(number.split('-')[1].replace('x', '9'))+1)]
            else:
                code_list += [i for i in range(int(number.replace('x', '0')), int(number.replace('x', '9'))+1)]
        else:
            if '-' in number:
                code_list += [i for i in range(int(number.split('-')[0]), int(number.split('-')[1])+1)]
            else:
                code_list += [number]
    return code_list

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
                'parent_id': "%s" %(parents.get(sheet.cell(row, element_name).value) if parents.get(sheet.cell(row, element_name).value) else ''),
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
                'parent_id': "%s" %(parent if not parents.get(sheet.cell(row, element_name).value) else parents.get(sheet.cell(row, element_name).value)),
                'sign': '-1' if sheet.cell(row, credit_debit).value == 'credit' else '1',
                'account_ids': get_range_domain(get_account_range(sheet, account, row)),
            })

read_sheet(resultatrakning, r_element_name, r_title, r_account_type, r_parents, r_credit_debit, r_lst)
read_sheet(balansrakning, b_element_name, b_title, b_account_type, b_parents, b_credit_debit, b_lst)


r_par = {}
for r in r_lst:
    # ~ print r['name'],r['element_name'], r['type'], r['parent_id']
    r_par[r['parent_id']] = ''
    

def mis_xml(r_lst,b_lst):
    def create_recs(data,record_id,main_record,name,desc,main_desc,lst,seq):
        ## Sub report
        record = ET.SubElement(data, 'record', id='%s' % record_id, model="mis.report")
        ET.SubElement(record, "field", name="name").text = main_desc

        kpi = ET.SubElement(data, 'record', id='mis_main_kpi_%s_%s' % (name,name), model="mis.report.kpi")
        ET.SubElement(kpi, "field", name="report_id",ref="%s" % main_record)
        ET.SubElement(kpi, "field", name="name").text = name
        ET.SubElement(kpi, "field", name="description").text = desc
        ET.SubElement(kpi, "field", name="style_id", ref="report_style_4")
        ET.SubElement(kpi, "field", name="auto_expand_accounts").text = 'True'
        ET.SubElement(kpi, "field", name="auto_expand_accounts_style_id", ref="report_style_2")
        ET.SubElement(kpi, "field", name="budgetable").text = 'True'
        ET.SubElement(kpi, "field", name="sequence").text = seq
        kpiexp = ET.SubElement(data, 'record', id='mis_main_kpi_exp_%s_%s' % (name,name), model="mis.report.kpi.expression")
        ET.SubElement(kpiexp, "field", name="kpi_id", ref='mis_main_kpi_%s_%s' % (name,name))
        ET.SubElement(kpiexp, "field", name="name").text = '%s.%s' % (name,name)



        ## Kpi
        
        
        kpi = ET.SubElement(data, 'record', id='mis_kpi_%s' % record_id, model="mis.report.kpi")
        ET.SubElement(kpi, "field", name="report_id",ref="%s" % record_id)
        ET.SubElement(kpi, "field", name="name").text = name
        ET.SubElement(kpi, "field", name="description").text = desc
        ET.SubElement(kpi, "field", name="auto_expand_accounts").text = 'True'
        ET.SubElement(kpi, "field", name="auto_expand_accounts_style_id", ref="report_style_2")
        ET.SubElement(kpi, "field", name="budgetable").text = 'True'
        ET.SubElement(kpi, "field", name="sequence").text = seq
        
        ## Subreport
        
        record =ET.SubElement(data, 'record', id='sub%s' % record_id, model="mis.report.subreport")
        ET.SubElement(record, "field", name="name").text = name
        ET.SubElement(record, "field", name="subreport_id", ref="%s" % record_id)
        ET.SubElement(record, "field", name="report_id", ref="report_rr")    

        kpiexpmain = ET.SubElement(data, 'record', id='mis_kpi_main_%s' % record_id, model="mis.report.kpi.expression")
        ET.SubElement(kpiexpmain, "field", name="kpi_id", ref='mis_kpi_%s' % record_id)
        account = []
        for rec in lst:
            if rec.get('parent_id') == record_id and rec.get('account_ids'):
                kpi = ET.SubElement(data, 'record', id='%s' % rec['element_name'], model="mis.report.kpi")
                ET.SubElement(kpi, "field", name="report_id",ref="%s" % record_id)
                ET.SubElement(kpi, "field", name="name").text = rec['element_name']
                ET.SubElement(kpi, "field", name="description").text = rec['name']
                ET.SubElement(kpi, "field", name="auto_expand_accounts").text = 'True'
                ET.SubElement(kpi, "field", name="auto_expand_accounts_style_id", ref="report_style_2")
                ET.SubElement(kpi, "field", name="budgetable").text = 'True'
                ET.SubElement(kpi, "field", name="sequence").text = seq
                kpiexp = ET.SubElement(data, 'record', id='mis_kpi_exp_%s' % rec['element_name'], model="mis.report.kpi.expression")
                ET.SubElement(kpiexp, "field", name="kpi_id", ref='%s' % rec['element_name'])
                ET.SubElement(kpiexp, "field", name="name").text = 'balp%s%s' % ([int(a) for a in rec.get('account_ids')],' * -1' if rec['sign'] == '-1' else '') 
                account.append(rec['element_name'])
        ET.SubElement(kpiexpmain, "field", name="name").text = ' + '.join(account)

    odoo = ET.Element('odoo')
    data = ET.SubElement(odoo, 'data')

    style = ET.SubElement(data, 'record', id='report_style_1', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style for money'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit",).text = "SEK"
    ET.SubElement(style, "field", name="dp_inherit", eval="False")
    ET.SubElement(style, "field", name="dp").text = "2"

    style = ET.SubElement(data, 'record', id='report_style_2', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style account'
    ET.SubElement(style, "field", name="indent_level_inherit", eval="False")
    ET.SubElement(style, "field", name="indent_level",).text = "1"
    ET.SubElement(style, "field", name="font_style_inherit", eval="False")
    ET.SubElement(style, "field", name="font_style").text = 'italic'

    style = ET.SubElement(data, 'record', id='report_style_3', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style total'
    ET.SubElement(style, "field", name="background_color_inherit", eval="False")
    ET.SubElement(style, "field", name="background_color",).text = "#967C8B"
    ET.SubElement(style, "field", name="color_inherit", eval="False")
    ET.SubElement(style, "field", name="color",).text = "#FFFFFF"
    ET.SubElement(style, "field", name="font_weight_inherit", eval="False")
    ET.SubElement(style, "field", name="font_weight").text = 'bold'

    style = ET.SubElement(data, 'record', id='report_style_4', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style bold'
    ET.SubElement(style, "field", name="font_weight_inherit", eval="False")
    ET.SubElement(style, "field", name="font_weight").text = 'bold'

    report_rr = ET.SubElement(data, 'record', id='report_rr', model="mis.report")
    ET.SubElement(report_rr, "field", name="name").text = u'Resultaträkning'
    # ~ field_style_id = ET.SubElement(record, "field", name="style_id", ref='mis_report_expenses_style1"')
    
    create_recs(data,'RorelsensIntakterLagerforandringarMmAbstract','report_rr','netto',u'Nettoomsättning',u'Intäkter',r_lst,'1')
    create_recs(data,'RorelsekostnaderAbstract','report_rr','kost',u'Kostnader','Kostnader',r_lst,'2')
    create_recs(data,'ResultatrakningKostnadsslagsindeladAbstract','report_rr','kostslag',u'Kostnadsslag',u'Kostnadsslag',r_lst,'3')
    create_recs(data,'RorelseresultatAbstract','report_rr','resultat',u'Resultat',u'Resultat',r_lst,'4')
    create_recs(data,'FinansiellaPosterAbstract','report_rr','fin',u'Finansiella poster',u'Finansiella poster',r_lst,'5')
    create_recs(data,'BokslutsdispositionerAbstract','report_rr','bokdisp',u'Bokslutsdispositioner',u'Bokslutsdispositioner',r_lst,'6')
    create_recs(data,'SkatterAbstract','report_rr','skatt',u'Skatter',u'Skatt',r_lst,'7')

    xml = minidom.parseString(ET.tostring(odoo)).toprettyxml(indent="    ")
    xml = xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')
    with open("../data/mis_financial_report.xml", "w") as f:
        f.write(xml.encode('utf-8'))
    print 'Finished'

mis_xml(r_lst, b_lst)

