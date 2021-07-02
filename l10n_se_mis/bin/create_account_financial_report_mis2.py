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
        account_range.append(sheet.cell(row, col + 1).value)
        col += 8
    return account_range


def get_range_domain(number_list):
    code_list = []
    for number in number_list:
        if 'x' in number:
            if '-' in number:
                code_list += [i for i in range(int(number.split('-')[0].replace('x', '0')),
                                               int(number.split('-')[1].replace('x', '9')) + 1)]
            else:
                code_list += [i for i in range(int(number.replace('x', '0')), int(number.replace('x', '9')) + 1)]
        else:
            if '-' in number:
                code_list += [i for i in range(int(number.split('-')[0]), int(number.split('-')[1]) + 1)]
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
                'name': sheet.cell(row, title).value.replace('(Presentation)', ''),
                'type': 'sum',
                'element_name': sheet.cell(row, element_name).value[:32],
                'parent_id': "%s" % (parents.get(sheet.cell(row, element_name).value) if parents.get(
                    sheet.cell(row, element_name).value) else ''),
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
                'element_name': sheet.cell(row, element_name).value[:32],
                'parent_id': "%s" % (parent if not parents.get(sheet.cell(row, element_name).value) else parents.get(
                    sheet.cell(row, element_name).value)),
                'sign': '-1' if sheet.cell(row, credit_debit).value == 'credit' else '1',
                'account_ids': get_range_domain(get_account_range(sheet, account, row)),
            })


read_sheet(resultatrakning, r_element_name, r_title, r_account_type, r_parents, r_credit_debit, r_lst)
read_sheet(balansrakning, b_element_name, b_title, b_account_type, b_parents, b_credit_debit, b_lst)


def mis_xml(r_lst, b_lst):
    def create_recs(data, rec, report_id, seq):
        def kpi(data, report_id, rec, report_style, seq):
            kpi = ET.SubElement(data, 'record', id='%s_%s' % (report_id, rec['element_name']), model="mis.report.kpi")
            ET.SubElement(kpi, "field", name="report_id", ref="%s" % report_id)
            ET.SubElement(kpi, "field", name="name").text = rec['element_name']
            ET.SubElement(kpi, "field", name="description").text = rec['name']
            ET.SubElement(kpi, "field", name="style_id", ref=report_style)
            ET.SubElement(kpi, "field", name="sequence").text = seq
            ET.SubElement(kpi, "field", name="auto_expand_accounts").text = 'True'
            ET.SubElement(kpi, "field", name="auto_expand_accounts_style_id", ref="report_style_2")

            if rec.get('account_ids'):
                ET.SubElement(kpi, "field", name="budgetable").text = 'True'
                kpiexp = ET.SubElement(data, 'record', id='kpi_title_%s_%s' % (report_id, rec['element_name']),
                                       model="mis.report.kpi.expression")
                ET.SubElement(kpiexp, "field", name="kpi_id", ref='%s_%s' % (report_id, rec['element_name']))
                ET.SubElement(kpiexp, "field", name="name").text = 'bal%s%s' % (
                [int(a) for a in rec['account_ids']], '* -1' if rec['sign'] == '-1' else '')

        kpi(data, '%s' % report_id, rec, 'report_style_1', seq)
        # ~ kpi(data,'%s_short' % report_id,rec,'report_style_2',seq)

    def create_title(data, rec, report_id, account_ids, report_style, seq):
        def kpi(data, report_id, rec, account_ids, report_style, seq):
            kpi = ET.SubElement(data, 'record', id='%s_%s_title' % (report_id, rec['element_name']),
                                model="mis.report.kpi")
            ET.SubElement(kpi, "field", name="report_id", ref="%s" % report_id)
            ET.SubElement(kpi, "field", name="name").text = rec['element_name']
            ET.SubElement(kpi, "field", name="description").text = rec['name']
            ET.SubElement(kpi, "field", name="style_id", ref=report_style)
            ET.SubElement(kpi, "field", name="type").text = 'str' if not account_ids else 'num'
            ET.SubElement(kpi, "field", name="budgetable").text = 'True' if account_ids else 'False'
            ET.SubElement(kpi, "field", name="sequence").text = seq
            if account_ids:
                kpiexp = ET.SubElement(data, 'record', id='kpi_title_%s_%s' % (report_id, rec['element_name']),
                                       model="mis.report.kpi.expression")
                ET.SubElement(kpiexp, "field", name="kpi_id", ref='%s_%s_title' % (report_id, rec['element_name']))
                ET.SubElement(kpiexp, "field", name="name").text = account_ids

        kpi(data, '%s' % report_id, rec, account_ids, report_style, seq)
        # ~ kpi(data,'%s_short' % report_id,rec,None,'report_style_2',seq)

    odoo = ET.Element('odoo')
    data = ET.SubElement(odoo, 'data')

    style = ET.SubElement(data, 'record', id='report_style_1', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style for money'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix", ).text = "SEK"
    ET.SubElement(style, "field", name="dp_inherit", eval="False")
    ET.SubElement(style, "field", name="dp").text = "0"
    ET.SubElement(style, "field", name="indent_level_inherit", eval="False")
    ET.SubElement(style, "field", name="indent_level", ).text = "2"

    style = ET.SubElement(data, 'record', id='report_style_2', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style account'
    ET.SubElement(style, "field", name="indent_level_inherit", eval="False")
    ET.SubElement(style, "field", name="indent_level", ).text = "4"
    ET.SubElement(style, "field", name="font_style_inherit", eval="False")
    ET.SubElement(style, "field", name="font_style").text = 'italic'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix", ).text = "SEK"

    style = ET.SubElement(data, 'record', id='report_style_3', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style total'
    ET.SubElement(style, "field", name="background_color_inherit", eval="False")
    ET.SubElement(style, "field", name="background_color", ).text = "#967C8B"
    ET.SubElement(style, "field", name="color_inherit", eval="False")
    ET.SubElement(style, "field", name="color", ).text = "#FFFFFF"
    ET.SubElement(style, "field", name="font_weight_inherit", eval="False")
    ET.SubElement(style, "field", name="font_weight").text = 'bold'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix", ).text = "SEK"

    style = ET.SubElement(data, 'record', id='report_style_4', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style bold'
    ET.SubElement(style, "field", name="font_weight_inherit", eval="False")
    ET.SubElement(style, "field", name="indent_level", ).text = "0"
    ET.SubElement(style, "field", name="font_weight").text = 'bold'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix", ).text = "SEK"

    style = ET.SubElement(data, 'record', id='report_style_5', model="mis.report.style")
    ET.SubElement(style, "field", name="name").text = u'Style bold sum'
    ET.SubElement(style, "field", name="font_weight_inherit", eval="False")
    ET.SubElement(style, "field", name="indent_level", ).text = "0"
    ET.SubElement(style, "field", name="font_weight").text = 'bold'
    # ~ ET.SubElement(style, "field", name="font_style_inherit", eval="False")
    # ~ ET.SubElement(style, "field", name="font_style").text = 'italic'
    ET.SubElement(style, "field", name="font_size_inherit", eval="False")
    ET.SubElement(style, "field", name="font_size").text = 'medium'
    ET.SubElement(style, "field", name="prefix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix_inherit", eval="False")
    ET.SubElement(style, "field", name="suffix", ).text = "SEK"

    report_rr = ET.SubElement(data, 'record', id='report_rr', model="mis.report")
    ET.SubElement(report_rr, "field", name="name").text = u'Resultaträkning'

    for seq, rec in enumerate(r_lst, start=1):
        if rec['parent_id'] == '' or rec['element_name'] == 'RavarorFornodenheterKostnader':
            continue

        if rec['element_name'] == 'RorelseresultatAbstract':
            create_title(data, rec, 'report_rr', None, 'report_style_3', '%s' % seq)

        elif rec['element_name'] == 'RorelseintakterLagerforandringar':
            create_title(data, rec, 'report_rr',
                         'Nettoomsattning+ForandringLagerProdukterIArbeteF+AktiveratArbeteEgenRakning+OvrigaRorelseintakter',
                         'report_style_5', '%s' % seq)
        # ~ 2 Rörelseresultat (Presentation) RorelseresultatAbstract title
        # ~ 3 Rörelseintäkter, lagerförändringar m.m. (Presentation) RorelsensIntakterLagerforandringarMmAbstract title
        # ~ 4 Nettoomsättning Nettoomsattning account
        # ~ 5 Förändringar av lager av produkter i arbete, färdiga varor och pågående arbeten för annans räkning ForandringLagerProdukterIArbeteF account
        # ~ 6 Aktiverat arbete för egen räkning AktiveratArbeteEgenRakning account
        # ~ 7 Övriga rörelseintäkter OvrigaRorelseintakter account
        # ~ 8 Rörelseintäkter, lagerförändringar m.m. RorelseintakterLagerforandringar title

        elif rec['element_name'] == 'Rorelsekostnader':
            # ~ create_title(data,rec,'report_rr','RavarorFornodenheterKostnader+HandelsvarorKostnader+OvrigaExternaKostnader+Personalkostnader+AvskrivningarNedskrivningarMater+NedskrivningarOmsattningstillgan+OvrigaRorelsekostnader','report_style_4','%s' % seq)
            create_title(data, rec, 'report_rr',
                         'HandelsvarorKostnader+OvrigaExternaKostnader+Personalkostnader+AvskrivningarNedskrivningarMater+NedskrivningarOmsattningstillgan+OvrigaRorelsekostnader',
                         'report_style_4', '%s' % seq)

        # ~ 9 Rörelsekostnader (Presentation) RorelsekostnaderAbstract title
        # ~ 10 Kostnad för förbrukning av råvaror och förnödenheter RavarorFornodenheterKostnader account
        # ~ 11 Kostnad för sålda handelsvaror HandelsvarorKostnader account
        # ~ 12 Övriga externa kostnader OvrigaExternaKostnader account
        # ~ 13 Personalkostnader Personalkostnader account
        # ~ 14 Av- och nedskrivningar av materiella och immateriella anläggningstillgångar AvskrivningarNedskrivningarMater account
        # ~ 15 Nedskrivningar av omsättningstillgångar utöver normala nedskrivningar NedskrivningarOmsattningstillgan account
        # ~ 16 Övriga rörelsekostnader OvrigaRorelsekostnader account
        # ~ 17 Rörelsekostnader Rorelsekostnader title

        elif rec['element_name'] == 'Rorelseresultat':
            create_title(data, rec, 'report_rr', 'RorelseintakterLagerforandringar-Rorelsekostnader', 'report_style_5',
                         '%s' % seq)
        # ~ 18 Rörelseresultat Rorelseresultat title

        elif rec['element_name'] == 'FinansiellaPoster':
            create_title(data, rec, 'report_rr',
                         'ResultatAndelarKoncernforetag+ResultatAndelarIntresseforetagGe+ResultatOvrigaforetagAgarintress+ResultatOvrigaFinansiellaAnlaggn+OvrigaRanteintakterLiknandeResul+NedskrivningarFinansiellaAnlaggn+RantekostnaderLiknandeResultatpo',
                         'report_style_5', '%s' % seq)
        # ~ 19 Finansiella poster (Presentation) FinansiellaPosterAbstract title
        # ~ 20 Resultat från andelar i koncernföretag ResultatAndelarKoncernforetag account
        # ~ 21 Resultat från andelar i intresseföretag och gemensamt styrda företag ResultatAndelarIntresseforetagGe account
        # ~ 22 Resultat från övriga företag som det finns ett ägarintresse i ResultatOvrigaforetagAgarintress account
        # ~ 23 Resultat från övriga finansiella anläggningstillgångar ResultatOvrigaFinansiellaAnlaggn account
        # ~ 24 Övriga ränteintäkter och liknande resultatposter OvrigaRanteintakterLiknandeResul account
        # ~ 25 Nedskrivningar av finansiella anläggningstillgångar och kortfristiga placeringar NedskrivningarFinansiellaAnlaggn account
        # ~ 26 Räntekostnader och liknande resultatposter RantekostnaderLiknandeResultatpo account
        # ~ 27 Summa finansiella poster FinansiellaPoster title

        elif rec['element_name'] == 'ResultatEfterFinansiellaPoster':
            create_title(data, rec, 'report_rr', 'Rorelseresultat-FinansiellaPoster', 'report_style_5', '%s' % seq)
        # ~ 28 Resultat efter finansiella poster ResultatEfterFinansiellaPoster title

        elif rec['element_name'] == 'Bokslutsdispositioner':
            create_title(data, rec, 'report_rr',
                         'ErhallnaKoncernbidrag+LamnadeKoncernbidrag+ForandringPeriodiseringsfond+ForandringOveravskrivningar+OvrigaBokslutsdispositioner',
                         'report_style_5', '%s' % seq)
        # ~ 29 Bokslutsdispositioner (Presentation) BokslutsdispositionerAbstract title
        # ~ 30 Erhållna koncernbidrag ErhallnaKoncernbidrag account
        # ~ 31 Lämnade koncernbidrag LamnadeKoncernbidrag account
        # ~ 32 Förändring av periodiseringsfonder ForandringPeriodiseringsfond account
        # ~ 33 Förändring av överavskrivningar ForandringOveravskrivningar account
        # ~ 34 Övriga bokslutsdispositioner OvrigaBokslutsdispositioner account
        # ~ 35 Summa bokslutsdispositioner Bokslutsdispositioner title

        elif rec['element_name'] == 'ResultatForeSkatt':
            create_title(data, rec, 'report_rr', 'ResultatEfterFinansiellaPoster-Bokslutsdispositioner',
                         'report_style_5', '%s' % seq)
        # ~ 36 Resultat före skatt ResultatForeSkatt title

        # ~ 37 Skatter (Presentation) SkatterAbstract title
        # ~ 38 Skatt på årets resultat SkattAretsResultat account
        # ~ 39 Övriga skatter OvrigaSkatter account
        # ~ 40 Årets resultat AretsResultat account

        elif rec.get('account_ids'):
            print
            seq, rec['name'], rec['element_name'], 'account'
            create_recs(data, rec, 'report_rr', '%s' % seq)
        else:
            print
            seq, rec['name'], rec['element_name'], 'title'
            create_title(data, rec, 'report_rr', None, 'report_style_4', '%s' % seq)

    report_rr = ET.SubElement(data, 'record', id='report_br', model="mis.report")
    ET.SubElement(report_rr, "field", name="name").text = u'Balansräkning'

    for seq, rec in enumerate(b_lst, start=1):
        if rec['parent_id'] == '':
            continue

        if rec['element_name'] == 'RorelseresultatAbstract':
            create_title(data, rec, 'report_br', None, 'report_style_3', '%s' % seq)

        # ~ 2 Tillgångar (Presentation) TillgangarAbstract title
        # ~ 3 Tecknat men ej inbetalt kapital TecknatEjInbetaltKapital account

        # ~ 4 Anläggningstillgångar (Presentation) AnlaggningstillgangarAbstract title
        # ~ 5 Immateriella anläggningstillgångar (Presentation) ImmateriellaAnlaggningstillganga title
        # ~ 6 Koncessioner, patent, licenser, varumärken samt liknande rättigheter KoncessionerPatentLicenserVaruma account
        # ~ 7 Hyresrätter och liknande rättigheter HyresratterLiknandeRattigheter account
        # ~ 8 Goodwill Goodwill account
        # ~ 9 Förskott avseende immateriella anläggningstillgångar ForskottImmateriellaAnlaggningst account
        # ~ 10 Immateriella anläggningstillgångar ImmateriellaAnlaggningstillganga account
        # ~ 11 Materiella anläggningstillgångar (Presentation) MateriellaAnlaggningstillgangarA title

        # ~ 12 Byggnader och mark ByggnaderMark account
        # ~ 13 Maskiner och andra tekniska anläggningar MaskinerAndraTekniskaAnlaggninga account
        # ~ 14 Inventarier, verktyg och installationer InventarierVerktygInstallationer account
        # ~ 15 Förbättringsutgifter på annans fastighet ForbattringsutgifterAnnansFastig account
        # ~ 16 Övriga materiella anläggningstillgångar OvrigaMateriellaAnlaggningstillg account
        # ~ 17 Pågående nyanläggningar och förskott avseende materiella anläggningstillgångar PagaendeNyanlaggningarForskottMa account

        elif rec['element_name'] == 'MateriellaAnlaggningstillgangar':  # Dublett med 13
            continue
        # ~ 18 Materiella anläggningstillgångar MateriellaAnlaggningstillgangar account

        # ~ 19 Finansiella anläggningstillgångar (Presentation) FinansiellaAnlaggningstillgangar title
        # ~ 20 Andelar i koncernföretag AndelarKoncernforetag account
        # ~ 21 Långfristiga fordringar hos koncernföretag FordringarKoncernforetagLangfris account
        # ~ 22 Andelar i intresseföretag och gemensamt styrda företag AndelarIntresseforetagGemensamtS account
        # ~ 23 Långfristiga fordringar hos intresseföretag och gemensamt styrda företag FordringarIntresseforetagGemensa account
        # ~ 24 Ägarintressen i övriga företag AgarintressenOvrigaForetag account
        # ~ 25 Långfristiga fordringar hos övriga företag som det finns ett ägarintresse i FordringarOvrigaForetagAgarintre account
        # ~ 26 Andra långfristiga värdepappersinnehav AndraLangfristigaVardepappersinn account
        # ~ 27 Lån till delägare eller närstående LanDelagareNarstaende account
        # ~ 28 Andra långfristiga fordringar AndraLangfristigaFordringar account
        # ~ 29 Finansiella anläggningstillgångar FinansiellaAnlaggningstillgangar account

        elif rec['element_name'] == 'Anlaggningstillgangar':
            create_title(data, rec, 'report_br', 'KoncessionerPatentLicenserVaruma+HyresratterLiknandeRattigheter+Goodwill+ForskottImmateriellaAnlaggningst+ \
            ImmateriellaAnlaggningstillganga+ByggnaderMark+MaskinerAndraTekniskaAnlaggninga+InventarierVerktygInstallationer+ForbattringsutgifterAnnansFastig+OvrigaMateriellaAnlaggningstillg+ \
            PagaendeNyanlaggningarForskottMa+AndelarKoncernforetag+FordringarKoncernforetagLangfris+AndelarIntresseforetagGemensamtS+FordringarIntresseforetagGemensa+ \
            AgarintressenOvrigaForetag+FordringarOvrigaForetagAgarintre+AndraLangfristigaVardepappersinn+LanDelagareNarstaende+AndraLangfristigaFordringar+FinansiellaAnlaggningstillgangar',
                         'report_style_5', '%s' % seq)
        # ~ 30 Anläggningstillgångar Anlaggningstillgangar title

        # ~ 31 Omsättningstillgångar (Presentation) OmsattningstillgangarAbstract title
        # ~ 32 Varulager m.m. (Presentation) VarulagerMmAbstract title
        # ~ 33 Lager av råvaror och förnödenheter LagerRavarorFornodenheter account
        # ~ 34 Lager av varor under tillverkning LagerVarorUnderTillverkning account
        # ~ 35 Lager av färdiga varor och handelsvaror LagerFardigaVarorHandelsvaror account
        # ~ 36 Övriga lagertillgångar OvrigaLagertillgangar account
        # ~ 37 Pågående arbeten för annans räkning (Tillgång) PagaendeArbetenAnnansRakningOmsa account
        # ~ 38 Förskott till leverantörer ForskottTillLeverantorer account
        # ~ 39 Varulager m.m. VarulagerMm account
        # ~ 40 Kortfristiga fordringar (Presentation) KortfristigaFordringarAbstract title
        # ~ 41 Kundfordringar Kundfordringar account
        # ~ 42 Kortfristiga fordringar hos koncernföretag FordringarKoncernforetagKortfris account
        # ~ 43 Kortfristiga fordringar hos intresseföretag och gemensamt styrda företag FordringarIntresseforetagGemensa account
        # ~ 44 Kortfristiga fordringar hos övriga företag som det finns ett ägarintresse i FordringarOvrigaforetagAgarintre account
        # ~ 45 Övriga kortfristga fordringar OvrigaFordringarKortfristiga account
        # ~ 46 Upparbetad men ej fakturerad intäkt UpparbetadEjFaktureradIntakt account
        # ~ 47 Förutbetalda kostnader och upplupna intäkter ForutbetaldaKostnaderUpplupnaInt account
        elif rec['element_name'] == 'KortfristigaFordringar':  # Dublett med 41 och 45
            continue
        # ~ 48 Kortfristiga fordringar KortfristigaFordringar account

        # ~ 49 Kortfristiga placeringar (Presentation) KortfristigaPlaceringarAbstract title
        # ~ 50 Kortfristiga andelar i koncernföretag AndelarKoncernforetagKortfristig account
        # ~ 51 Övriga kortfristiga placeringar OvrigaKortfristigaPlaceringar account
        # ~ 52 Kortfristiga placeringar KortfristigaPlaceringar account
        # ~ 53 Kassa och bank (Presentation) KassaBankAbstract title
        # ~ 54 Kassa och bank exklusive redovisningsmedel KassaBankExklRedovisningsmedel account
        # ~ 55 Redovisningsmedel Redovisningsmedel account
        elif rec['element_name'] == 'KassaBank':
            create_title(data, rec, 'report_br', 'KassaBankExklRedovisningsmedel+Redovisningsmedel', 'report_style_5',
                         '%s' % seq)

        # ~ 56 Kassa och bank KassaBank title
        elif rec['element_name'] == 'Omsattningstillgangar':
            create_title(data, rec, 'report_br', 'LagerRavarorFornodenheter+LagerVarorUnderTillverkning+LagerFardigaVarorHandelsvaror+OvrigaLagertillgangar+PagaendeArbetenAnnansRakningOmsa+ \
                ForskottTillLeverantorer+VarulagerMm+Kundfordringar+FordringarKoncernforetagKortfris+FordringarIntresseforetagGemensa+OvrigaFordringarKortfristiga+UpparbetadEjFaktureradIntakt+ \
                ForutbetaldaKostnaderUpplupnaInt+AndelarKoncernforetagKortfristig+OvrigaKortfristigaPlaceringar+KortfristigaPlaceringar+KassaBank',
                         'report_style_5', '%s' % seq)

        # ~ 57 Omsättningstillgångar Omsattningstillgangar title
        elif rec['element_name'] == 'Tillgangar':
            create_title(data, rec, 'report_br', 'Anlaggningstillgangar+Omsattningstillgangar', 'report_style_5',
                         '%s' % seq)
        # ~ 58 Tillgångar Tillgangar title

        # ~ 59 Eget kapital och skulder (Presentation) EgetKapitalSkulderAbstract title
        # ~ 60 Eget kapital (Presentation) EgetKapitalAbstract title
        # ~ 61 Bundet eget kapital (Presentation) BundetEgetKapitalAbstract title
        # ~ 62 Aktiekapital Aktiekapital account
        # ~ 63 Ej registrerat aktiekapital EjRegistreratAktiekapital account
        # ~ 64 Uppskrivningsfond Uppskrivningsfond account
        # ~ 65 Reservfond Reservfond account
        elif rec['element_name'] == 'BundetEgetKapital':
            create_title(data, rec, 'report_br', 'Aktiekapital+EjRegistreratAktiekapital+Uppskrivningsfond+Reservfond',
                         'report_style_5', '%s' % seq)
        # ~ 66 Bundet eget kapital BundetEgetKapital title

        # ~ 67 Fritt eget kapital (Presentation) FrittEgetKapitalAbstract title

        # ~ 68 Överkursfond Overkursfond account
        # ~ 69 Balanserat resultat BalanseratResultat account

        # ~ 70 Årets resultat i balansräkningen AretsResultatEgetKapital account
        elif rec['element_name'] == 'FrittEgetKapital':
            create_title(data, rec, 'report_br', 'Overkursfond+BalanseratResultat+AretsResultatEgetKapital',
                         'report_style_5', '%s' % seq)
        # ~ 71 Fritt eget kapital FrittEgetKapital title
        elif rec['element_name'] == 'EgetKapital':
            create_title(data, rec, 'report_br', 'FrittEgetKapital+BundetEgetKapital', 'report_style_5', '%s' % seq)
        # ~ 72 Eget kapital EgetKapital title

        # ~ 73 Obeskattade reserver (Presentation) ObeskattadeReserverAbstract title
        # ~ 74 Periodiseringsfonder Periodiseringsfonder account
        # ~ 75 Ackumulerade överavskrivningar AckumuleradeOveravskrivningar account
        # ~ 76 Övriga obeskattade reserver OvrigaObeskattadeReserver account
        elif rec['element_name'] == 'ObeskattadeReserver':  # Dublett med 08, 103, 104, 105
            continue
        # ~ 77 Obeskattade reserver ObeskattadeReserver account
        # ~ 78 Avsättningar (Presentation) AvsattningarAbstract title
        # ~ 79 Avsättningar för pensioner och liknande förpliktelser enligt lagen (1967:531) om tryggande av pensionsutfästelse m.m. AvsattningarPensionerLiknandeFor account
        # ~ 80 Övriga avsättningar för pensioner och liknande förpliktelser OvrigaAvsattningarPensionerLikna account
        # ~ 81 Övriga avsättningar OvrigaAvsattningar account
        elif rec['element_name'] == 'Avsattningar':
            create_title(data, rec, 'report_br', 'Periodiseringsfonder+AckumuleradeOveravskrivningar+OvrigaObeskattadeReserver+ \
                AvsattningarPensionerLiknandeFor+OvrigaAvsattningarPensionerLikna+OvrigaAvsattningar', 'report_style_5',
                         '%s' % seq)
        # ~ 82 Avsättningar Avsattningar title

        # ~ 83 Långfristiga skulder (Presentation) LangfristigaSkulderAbstract title
        # ~ 84 Obligationslån Obligationslan account
        # ~ 85 Långfristig checkräkningskredit CheckrakningskreditLangfristig account
        # ~ 86 Övriga långfristiga skulder till kreditinstitut OvrigaLangfristigaSkulderKrediti account
        # ~ 87 Långfristiga skulder till koncernföretag SkulderKoncernforetagLangfristig account
        # ~ 88 Långfristiga skulder till intresseföretag och gemensamt styrda företag SkulderIntresseforetagGemensamtS account
        # ~ 89 Långfristiga skulder till övriga företag som det finns ett ägarintresse i SkulderOvrigaForetagAgarintresse account
        # ~ 90 Övriga långfristiga skulder OvrigaLangfristigaSkulder account
        # ~ 91 Långfristiga skulder LangfristigaSkulder account
        # ~ 92 Kortfristiga skulder (Presentation) KortfristigaSkulderAbstract title
        # ~ 93 Kortfristig checkräkningskredit  CheckrakningskreditKortfristig account
        # ~ 94 Övriga kortfristiga skulder till kreditinstitut OvrigaKortfristigaSkulderKrediti account
        # ~ 95 Förskott från kunder ForskottFranKunder account
        # ~ 96 Pågående arbeten för annans räkning (Skuld) PagaendeArbetenAnnansRakningKort account
        # ~ 97 Fakturerad men ej upparbetad intäkt FaktureradEjUpparbetadIntakt account
        # ~ 98 Leverantörsskulder Leverantorsskulder account
        # ~ 99 Växelskulder Vaxelskulder account
        # ~ 100 Kortfristiga skulder till koncernföretag SkulderKoncernforetagKortfristig account
        # ~ 101 Kortfristiga skulder till intresseföretag och gemensamt styrda företag SkulderIntresseforetagGemensamtS account
        # ~ 102 Kortfristiga skulder till övriga företag som det finns ett ägarintresse i SkulderOvrigaForetagAgarintresse account
        # ~ 103 Skatteskulder Skatteskulder account
        # ~ 104 Övriga kortfristiga skulder OvrigaKortfristigaSkulder account
        # ~ 105 Upplupna kostnader och förutbetalda intäkter UpplupnaKostnaderForutbetaldaInt account
        elif rec['element_name'] == 'KortfristigaSkulder':  # Dublett med 08, 103, 104, 105
            continue
        # ~ 106 Kortfristiga skulder KortfristigaSkulder account

        elif rec['element_name'] == 'EgetKapitalSkulder':
            create_title(data, rec, 'report_br', 'Obligationslan+CheckrakningskreditLangfristig+OvrigaLangfristigaSkulderKrediti+ \
                    SkulderKoncernforetagLangfristig+SkulderIntresseforetagGemensamtS+SkulderOvrigaForetagAgarintresse+OvrigaLangfristigaSkulder+ \
                    LangfristigaSkulder+CheckrakningskreditKortfristig+OvrigaKortfristigaSkulderKrediti+ForskottFranKunder+ \
                    PagaendeArbetenAnnansRakningKort+FaktureradEjUpparbetadIntakt+Leverantorsskulder+Vaxelskulder+SkulderKoncernforetagKortfristig+ \
                    SkulderOvrigaForetagAgarintresse+Skatteskulder+OvrigaKortfristigaSkulder+UpplupnaKostnaderForutbetaldaInt',
                         'report_style_5', '%s' % seq)
        # ~ 107 Eget kapital och skulder EgetKapitalSkulder title

        elif rec.get('account_ids'):
            print
            seq, rec['name'], rec['element_name'], 'account'
            create_recs(data, rec, 'report_br', '%s' % seq)
        else:
            print
            seq, rec['name'], rec['element_name'], 'title'
            create_title(data, rec, 'report_br', None, 'report_style_4', '%s' % seq)

    xml = minidom.parseString(ET.tostring(odoo)).toprettyxml(indent="    ")
    xml = xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>')
    with open("../data/mis_financial_report.xml", "w") as f:
        f.write(xml.encode('utf-8'))
    print
    'Finished'


mis_xml(r_lst, b_lst)
