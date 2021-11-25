# -*- coding: utf-8 -*-
try:
    from xlrd import open_workbook
    import xml.etree.cElementTree as ET
    from xml.dom import minidom
except ImportError:
    pass
import logging
_logger = logging.getLogger(__name__)

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

# key: element_name
# value: external_id

external_id_exchange_dict = {
    'Kundfordringar': 'account.data_account_type_receivable',
    'Leverantorsskulder': 'account.data_account_type_payable',
    'KassaBankExklRedovisningsmedel': 'account.data_account_type_liquidity',
    'CheckrakningskreditKortfristig': 'account.data_account_type_credit_card',
    'OvrigaFordringarKortfristiga': 'account.data_account_type_current_assets',
    'KoncessionerPatentLicenserVarumarkenLiknandeRattigheter': 'account.data_account_type_non_current_assets',
    'ForskottFranKunder': 'account.data_account_type_prepayments',
    'MaskinerAndraTekniskaAnlaggningar': 'account.data_account_type_fixed_assets',
    'OvrigaKortfristigaSkulder': 'account.data_account_type_current_liabilities',
    'OvrigaLangfristigaSkulderKreditinstitut': 'account.data_account_type_non_current_liabilities',
    'Aktiekapital': 'account.data_account_type_equity',
    # ~ 'AretsResultat': 'account.data_unaffected_earnings', # har en sql constrains som gör så att vi inte får ha fler en ett konto
    'OvrigaRorelseintakter': 'account.data_account_type_other_income',
    'Nettoomsattning': 'account.data_account_type_revenue',
    'AvskrivningarNedskrivningarMateriellaImmateriellaAnlaggningstillgangar': 'account.data_account_type_depreciation',
    'OvrigaRorelsekostnader': 'account.data_account_type_expenses',
    'HandelsvarorKostnader': 'account.data_account_type_direct_costs',
}

# ~ https://www.fortnox.se/fortnox-foretagsguide/ekonomisk-ordlista/kontoklasser/  |Har en lista om vad dem olika konto klasserna generellt används till.
# ~ https://www.bas.se/wp-content/uploads/2017/06/Kontoplan_Normal_2021.pdf  |
# ~ https://www.bjornlunden.se/skatt/obeskattade-reserver__470 							| Obeskattade reserver. 2100-2199  Är mellan Skuld och eget kapital. Men tydligen är skylden "dold" så jag satte den som kapital.
# ~ https://www.arsredovisning-online.se/bas_kontoplan 											| Detta användes för account types som inte hade en account range för att kolla vilka konton det handlade om.
# ~ https://www.bokforingstips.se/artikel/bokforing/koncernbidrag.aspx 					| Erhållna Koncernbidrag och lämnade Koncernbidrag
# ~ https://vismaspcs.se/ekonomiska-termer/vad-ar-periodiseringsfond                   | Förändring av periodiseringsfonder, tas upp som en kostnad vid upprättning av en periodiseringsfond tas den upp i resultaträkningen som en kostnad 
# ~ https://www.bjornlunden.se/bokf%C3%B6ring/%C3%B6veravskrivning__2359	|Förändring av överavskrivningar. 
# ~ https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/enskildnaringsverksamhet/periodiseringsfond.4.361dc8c15312eff6fd2b8f2.html | Periodiseringsfonder, verkar som att man skuter upp en del skatter för att betala senare. Vilket Jag skulle klassificera som en skuld.
# ~ https://www.bjornlunden.se/bokf%C3%B6ring/ackumulerade-%C3%B6veravskrivningar__551  |Ackumulerade överavskrivningar, Satte den som en skuld. 
#	The 'Internal Group' is used to filter accounts based on the internal group set on the account type. Så jag tänker anta att det inte är jätte viktigt att jag sätter precis rätt internal group för varje account_account_type.
# Odoo 13 requires that internal_group has one of the following values set on account.account.type
# ~ equity	Eget kapital
# ~ asset	Tillgång
# ~ liability	Skuld
# ~ income	Nettoomsättning
# ~ expense	Utlägg
# ~ off_balance	Off Balance

internal_group_dict = {
'Nettoomsättning':'income',
'Förändringar av lager av produkter i arbete, färdiga varor och pågående arbeten för annans räkning':'expense',
'Aktiverat arbete för egen räkning':'income',
'Övriga rörelseintäkter':'income',
'Kostnad för förbrukning av råvaror och förnödenheter':'expense',
'Kostnad för sålda handelsvaror':'expense',
'Övriga externa kostnader':'expense',
'Personalkostnader':'expense',
'Av- och nedskrivningar av materiella och immateriella anläggningstillgångar':'expense',
'Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar':'expense',
'Övriga rörelsekostnader':'expense',
'Resultat från andelar i koncernföretag':'income',
'Resultat från andelar i intresseföretag och gemensamt styrda företag':'income',
'Resultat från övriga företag som det finns ett ägarintresse i':'income',
'Resultat från övriga företag som det finns ett ägarintresse i':'income',
'Resultat från övriga finansiella anläggningstillgångar':'income',
'Övriga ränteintäkter och liknande resultatposter':'income',
'Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar':'expense',
'Räntekostnader och liknande resultatposter':'expense',
'Erhållna koncernbidrag':'income',
'Lämnade koncernbidrag':'expense',
'Förändring av periodiseringsfonder':'expense',
'Förändring av överavskrivningar':'expense',
'Övriga bokslutsdispositioner':'income',
'Skatt på årets resultat':'expense',
'Övriga skatter':'expense',
'Årets resultat':'income',
'Tecknat men ej inbetalt kapital':'asset',
'Koncessioner, patent, licenser, varumärken samt liknande rättigheter':'asset',
'Hyresrätter och liknande rättigheter':'asset',
'Goodwill':'asset',
'Förskott avseende immateriella anläggningstillgångar':'asset',
'Byggnader och mark':'asset',
'Maskiner och andra tekniska anläggningar':'asset',
'Inventarier, verktyg och installationer':'asset',
'Förbättringsutgifter på annans fastighet':'asset',
'Övriga materiella anläggningstillgångar':'asset',
'Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar':'asset',
'Andelar i koncernföretag':'asset',
'Långfristiga fordringar hos koncernföretag':'asset',
'Andelar i intresseföretag och gemensamt styrda företag':'asset',
'Långfristiga fordringar hos intresseföretag och gemensamt styrda företag':'asset',
'Ägarintressen i övriga företag':'asset',
'Långfristiga fordringar hos övriga företag som det finns ett ägarintresse i':'asset',
'Andra långfristiga värdepappersinnehav':'asset',
'Lån till delägare eller närstående':'asset',
'Andra långfristiga fordringar':'asset',
'Lager av råvaror och förnödenheter':'asset',
'Lager av varor under tillverkning':'asset',
'Lager av färdiga varor och handelsvaror':'asset',
'Övriga lagertillgångar':'asset',
'Pågående arbeten för annans räkning (Tillgång)':'asset',
'Förskott till leverantörer':'asset',
'Kundfordringar':'asset',
'Kortfristiga fordringar hos koncernföretag,':'asset',
'Kortfristiga fordringar hos koncernföretag':'asset',
'Kortfristiga fordringar hos intresseföretag och gemensamt styrda företag':'asset',
'Kortfristiga fordringar hos övriga företag som det finns ett ägarintresse i':'asset',
'Övriga kortfristga fordringar':'asset',
'Upparbetad men ej fakturerad intäkt':'asset',
'Förutbetalda kostnader och upplupna intäkter':'asset',
'Kortfristiga andelar i koncernföretag':'asset',
'Övriga kortfristiga placeringar':'asset',
'Kassa och bank exklusive redovisningsmedel':'asset',
'Redovisningsmedel':'asset',
'Aktiekapital':'equity',
'Ej registrerat aktiekapital':'equity',
'Uppskrivningsfond':'equity',
'Reservfond':'equity',
'Överkursfond':'equity',
'Balanserat resultat':'equity',
'Årets resultat i balansräkningen':'equity',
'Periodiseringsfonder':'liability',
'Ackumulerade överavskrivningar':'liability',
'Övriga obeskattade reserver':'equity',
'Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelse m.m.':'liability',
'Övriga avsättningar för pensioner och liknande förpliktelser':'liability',
'Övriga avsättningar':'liability',
'Obligationslån':'equity',
'Långfristig checkräkningskredit':'liability',
'Övriga långfristiga skulder till kreditinstitut':'liability',
'Långfristiga skulder till koncernföretag':'liability',
'Långfristiga skulder till intresseföretag och gemensamt styrda företag':'liability',
'Långfristiga skulder till övriga företag som det finns ett ägarintresse i':'liability',
'Övriga långfristiga skulder':'liability',
'Kortfristig checkräkningskredit ':'liability',
'Här redovisas den del av en utnyttjad kredit som inte bedöms vara en långfristig finansiering':'liability',
'Övriga kortfristiga skulder till kreditinstitut':'liability',
'Förskott från kunder':'equity',
'Pågående arbeten för annans räkning (Skuld)':'liability',
'Fakturerad men ej upparbetad intäkt':'equity',
'Leverantörsskulder':'liability',
'Växelskulder':'liability',
'Kortfristiga skulder till koncernföretag':'liability',
'Kortfristiga skulder till intresseföretag och gemensamt styrda företag':'liability',
'Kortfristiga skulder till övriga företag som det finns ett ägarintresse i':'liability',
'Skatteskulder':'liability',
'Övriga kortfristiga skulder':'liability',
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

def get_type(lst):
    if '1930' in lst:
        return 'liquidity'
    elif '2440' in lst:
        return 'payable'
    elif '1510' in lst:
        return 'receivable'
    elif '2820' in lst:
        return 'other'
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

def print_xml(sheet_list):
    def parse_xml(sheet_list):
        odoo = ET.Element('odoo')
        data = ET.SubElement(odoo, 'data')
        _logger.warning(external_id_exchange_dict)
        for lst in sheet_list:
            for l in lst:
                external_id = external_id_exchange_dict.get(l.get('element_name'), 'type_%s' %l.get('element_name'))
                _logger.warning(f"external: {external_id}")
                record = ET.SubElement(data, 'record', id=external_id, model="account.account.type")
                field_name = ET.SubElement(record, "field", name="name").text = l.get('name')
                field_element_name = ET.SubElement(record, "field", name="element_name").text = l.get('element_name')
                field_type = ET.SubElement(record, "field", name="type").text = l.get('type')
                field_main_type = ET.SubElement(record, "field", name="main_type").text = l.get('main_type')
                field_report_type = ET.SubElement(record, "field", name="report_type").text = l.get('report_type')
                field_account_range = ET.SubElement(record, "field", name="account_range").text = str(l.get('account_range'))
                field_note = ET.SubElement(record, "field", name="note").text = l.get('note')
                if l.get('name') not in internal_group_dict:
                    raise Exception("Hittade ett par konton som inte finns i internal_group_dict. Någon borde kolla vart \""+ str(l.get('name')) +  "\" tillhör och lägga till dem i dicten")
                field_internal_group = ET.SubElement(record, "field", name="internal_group").text = internal_group_dict.get(str(l.get('name')))
                
        #Missing a group from the sheet that we read, so I'll add that one here. Övrigt bundet kapital
        external_id = "type_OvrigaBundetKapital"
        record = ET.SubElement(data, 'record', id=external_id, model="account.account.type")
        field_name = ET.SubElement(record, "field", name="name").text = "Övrigt bundet kapital"
        field_element_name = ET.SubElement(record, "field", name="element_name").text = "OvrigtBundetKapital"
        field_type = ET.SubElement(record, "field", name="type").text = "other"
        field_main_type = ET.SubElement(record, "field", name="main_type").text = "TillgangarAbstract"
        field_report_type = ET.SubElement(record, "field", name="report_type").text = "b"
        field_account_range = ET.SubElement(record, "field", name="account_range").text = "[('code', 'in', ['2087', '2088', '2089'])]"
        field_note = ET.SubElement(record, "field", name="note").text = ""
        field_internal_group = ET.SubElement(record, "field", name="internal_group").text = "asset"
        
        #Missing a group from the sheet that we read, so I'll add that one here. Upplupna kostnader och förutbetalda intäkter 
        
        external_id = "type_UpplupnaKostnaderForutbetaldaIntakter"
        record = ET.SubElement(data, 'record', id=external_id, model="account.account.type")
        field_name = ET.SubElement(record, "field", name="name").text = "Upplupna kostnader och förutbetalda intäkter"
        field_element_name = ET.SubElement(record, "field", name="element_name").text = "UpplupnaKostnaderForutbetaldaIntakter"
        field_type = ET.SubElement(record, "field", name="type").text = "other"
        field_main_type = ET.SubElement(record, "field", name="main_type").text = "TillgangarAbstract"
        field_report_type = ET.SubElement(record, "field", name="report_type").text = "b"
        field_account_range = ET.SubElement(record, "field", name="account_range").text = f"[('code', 'in', {[str(x) for x in range(2900, 3000)]})]" 
        field_note = ET.SubElement(record, "field", name="note").text = ""
        field_internal_group = ET.SubElement(record, "field", name="internal_group").text = "asset"

        
        #End of hard code
        ET.SubElement(data, 'function', name='_change_name', model="account.account.type")

        return odoo
    xml = minidom.parseString(ET.tostring(parse_xml(sheet_list))).toprettyxml(indent="    ")
    xml = xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')
    with open("../data/account_account_type.xml", "w") as f:
        f.write(xml)

print_xml([r_lst, b_lst])

# ~ # Test script
# ~ print """<?xml version="1.0" encoding="utf-8"?>
# ~ <odoo>
    # ~ <data>
# ~ """

# ~ for r in r_lst:
    # ~ print """        <record id="type_%s" model="account.account.type">
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
    # ~ print """        <record id="type_%s" model="account.account.type">
            # ~ <field name="name">%s</field>
            # ~ <field name="type">%s</field>
            # ~ <field name="element_name">%s</field>
            # ~ <field name="main_type">%s</field>
            # ~ <field name="report_type">%s</field>
            # ~ <field name="account_range">%s</field>
            # ~ <field name="note">%s</field>
        # ~ </record>
    # ~ """ %(b.get('element_name'), b.get('name'), b.get('type'), b.get('element_name'), b.get('main_type'), b.get('report_type'), b.get('account_range'), b.get('note'))

# ~ print """    </data>
# ~ </odoo>
# ~ """





