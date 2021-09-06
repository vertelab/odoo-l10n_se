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
    'AretsResultat': 'account.data_unaffected_earnings',
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
        for lst in sheet_list:
            for l in lst:
                external_id = external_id_exchange_dict.get(l.get('element_name'), 'type_%s' %l.get('element_name'))
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
        ET.SubElement(data, 'function', name='_change_name', model="account.account.type")
        return odoo
    xml = minidom.parseString(ET.tostring(parse_xml(sheet_list))).toprettyxml(indent="    ")
    xml = xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')
    # ~ with open("../data/account_account_type.xml", "w") as f:
    with open("../data/account_account_type_new.xml", "wb") as f:
        f.write(xml.encode('utf-8'))

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


# ~ Nettoomsättning, 																																			3000-3799,	   asset
# ~ Förändringar av lager av produkter i arbete, färdiga varor och pågående arbeten för annans räkning, 4932-4979,   expense
# ~ Aktiverat arbete för egen räkning,																													3800-3899,	   asset
# ~ Övriga rörelseintäkter,																																	3900-3999,	   asset
# ~ Kostnad för förbrukning av råvaror och förnödenheter,																				4000-4931,	   expense
# ~ Kostnad för sålda handelsvaror,																													4000-4989
# ~ Övriga externa kostnader,																																5000-6999
# ~ Personalkostnader, 																																		7000-7699
# ~ Av- och nedskrivningar av materiella och immateriella anläggningstillgångar,											7710-7849
# ~ Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar,													7740-7799
# ~ Övriga rörelsekostnader,																																7960-7999
# ~ Resultat från andelar i koncernföretag,																											8010-8039
# ~ Resultat från andelar i intresseföretag och gemensamt styrda företag,														8111-8132
# ~ Resultat från övriga företag som det finns ett ägarintresse i,																		8113-8133
# ~ Resultat från övriga finansiella anläggningstillgångar,																					8210-8269
# ~ Övriga ränteintäkter och liknande resultatposter,																							8310-8399
# ~ Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar,										8070-8389
# ~ Räntekostnader och liknande resultatposter,																								8400-8499
# ~ Erhållna koncernbidrag,																																	8820-8829
# ~ Lämnade koncernbidrag,																																8830-8839
# ~ Förändring av periodiseringsfonder,																												8810-8819
# ~ Förändring av överavskrivningar,																													8850-8859
# ~ Övriga bokslutsdispositioner,																															8860-8899
# ~ Skatt på årets resultat,																																	8910-8939
# ~ Övriga skatter,																																					8980-8989
# ~ Årets resultat,																																					8990-8999
# ~ Tecknat men ej inbetalt kapital,																														1690-1699
# ~ Koncessioner, patent, licenser, varumärken samt liknande rättigheter,														1020-1059
# ~ Hyresrätter och liknande rättigheter,																												1060-1069
# ~ Goodwill,																																							1070-1079
# ~ Förskott avseende immateriella anläggningstillgångar,																				1080-1089
# ~ Byggnader och mark,																																		1110-1159
# ~ Maskiner och andra tekniska anläggningar,																									1210-1219
# ~ Inventarier, verktyg och installationer, 																											1220-1259
# ~ Förbättringsutgifter på annans fastighet, 																										1120-1129
# ~ Övriga materiella anläggningstillgångar, 																										1290-1299
# ~ Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar,								1180-1289
# ~ Andelar i koncernföretag, 																																1310-1319
# ~ Långfristiga fordringar hos koncernföretag,																									tom
# ~ Andelar i intresseföretag och gemensamt styrda företag,																			tom
# ~ Långfristiga fordringar hos intresseföretag och gemensamt styrda företag,
# ~ Ägarintressen i övriga företag,
# ~ Långfristiga fordringar hos övriga företag som det finns ett ägarintresse i,													1346', '1347'
# ~ Andra långfristiga värdepappersinnehav,
# ~ Lån till delägare eller närstående,
# ~ Andra långfristiga fordringar,
# ~ Lager av råvaror och förnödenheter,
# ~ Lager av varor under tillverkning,
# ~ Lager av färdiga varor och handelsvaror,
# ~ Övriga lagertillgångar,																																	1490-1499
# ~ Pågående arbeten för annans räkning (Tillgång)	,																						tom
# ~ Förskott till leverantörer,
# ~ Kundfordringar,
# ~ Kortfristiga fordringar hos koncernföretag,
# ~ Kortfristiga fordringar hos intresseföretag och gemensamt styrda företag
# ~ Kortfristiga fordringar hos övriga företag som det finns ett ägarintresse i
# ~ Övriga kortfristga fordringar
# ~ Upparbetad men ej fakturerad intäkt
# ~ Förutbetalda kostnader och upplupna intäkter
# ~ Kortfristiga andelar i koncernföretag
# ~ Övriga kortfristiga placeringar
# ~ Kassa och bank exklusive redovisningsmedel
# ~ Redovisningsmedel
# ~ Aktiekapital
# ~ Ej registrerat aktiekapital
# ~ Uppskrivningsfond
# ~ Reservfond
# ~ Överkursfond
# ~ Balanserat resultat
# ~ Årets resultat i balansräkningen
# ~ Periodiseringsfonder
# ~ Ackumulerade överavskrivningar
# ~ Övriga obeskattade reserver
# ~ Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelse m.m.
# ~ Övriga avsättningar för pensioner och liknande förpliktelser
# ~ Övriga avsättningar
# ~ Obligationslån
# ~ Långfristig checkräkningskredit
# ~ Övriga långfristiga skulder till kreditinstitut
# ~ Långfristiga skulder till koncernföretag
# ~ Långfristiga skulder till intresseföretag och gemensamt styrda företag
# ~ Långfristiga skulder till övriga företag som det finns ett ägarintresse i
# ~ Övriga långfristiga skulder
# ~ Kortfristig checkräkningskredit 
# ~ Här redovisas den del av en utnyttjad kredit som inte bedöms vara en långfristig finansiering
# ~ Övriga kortfristiga skulder till kreditinstitut
# ~ Förskott från kunder
# ~ Pågående arbeten för annans räkning (Skuld)
# ~ Fakturerad men ej upparbetad intäkt
# ~ Leverantörsskulder
# ~ Växelskulder
# ~ Kortfristiga skulder till koncernföretag
# ~ Kortfristiga skulder till intresseföretag och gemensamt styrda företag
# ~ Kortfristiga skulder till övriga företag som det finns ett ägarintresse i
# ~ Skatteskulder
# ~ Övriga kortfristiga skulder
