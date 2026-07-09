#!/usr/bin/env python3
"""
Gemensam basgenerator för MIS XML från Excel-taxonomi.
Används av: l10n_se_mis_k2, l10n_se_mis_k2_filial, l10n_se_mis_k2_forening,
            l10n_se_mis_k2_handelsbolag, l10n_se_mis_k3, l10n_se_mis_k3_koncern

Kör via respektive moduls generate_mis_xml.py som importerar denna modul.

Fixes v2:
- Expand narrow BAS ranges (26xx→2600-2669, 27xx→2700-2799, 17xx→1700-1799, 29xx→2900-2999 etc.)
- Track hierarchy via display columns (E-H) for parent_id
- Aggregate sum KPIs by collecting all accounts from their children
"""
import os
from openpyxl import load_workbook

# ── Expanded BAS range overrides ──────────────────────────────────────────────
# The K2/K3 taxonomies use narrow xx-suffix patterns (e.g. 26xx → 2600-2609)
# but real BAS plans have wider ranges. These overrides extend them.
BAS_RANGE_EXPANSIONS = {
    '26xx': range(2600, 2670),    # 2600-2669 includes all VAT accounts
    '27xx': range(2700, 2800),    # 2700-2799 personal taxes + other
    '29xx': range(2900, 3000),    # 2900-2999 accrued expenses + prepaid income
    '17xx': range(1700, 1800),    # 1700-1799 prepaid expenses + accrued income
    '20xx': range(2000, 2100),    # 2000-2099 all equity accounts
    '209x': range(2090, 2100),    # 2090-2099
    '208x': range(2080, 2090),    # 2080-2089
}

# ── Negate (credit) mappings for aggregated sum KPIs ─────────────────────────
# Sum KPIs without own BAS accounts inherit negate from their section type
ASSET_SUM_KPIS = ('Tillgangar', 'Omsattningstillgangar', 'Anlaggningstillgangar',
                  'TecknatEjInbetaltKapital')
LIABILITY_SUM_KPIS = ('EgetKapitalSkulder', 'EgetKapital', 'KortfristigaSkulder',
                      'LangfristigaSkulder', 'Avsattningar', 'ObeskattadeReserver',
                      'BundetEgetKapital', 'FrittEgetKapital',
                      'RorelseintakterLagerforandringarMm', 'Rorelsekostnader',
                      'FinansiellaPoster', 'ResultatEfterFinansiellaPoster',
                      'ResultatEfterBokslutsdispositioner', 'AretsResultat',
                      'Rorelseresultat')


def expand_bas_range(bas_str):
    """Expandera BAS-konto range som '191x-198x' eller '1331-1334' till lista.
    Uses BAS_RANGE_EXPANSIONS for wider ranges where the taxonomy is too narrow."""
    if not bas_str:
        return []
    bas_str = bas_str.strip()
    if bas_str in BAS_RANGE_EXPANSIONS:
        return sorted(BAS_RANGE_EXPANSIONS[bas_str])
    accounts = []
    if '/' in bas_str:
        bas_str = bas_str.split('/')[-1]
    if '-' in bas_str:
        parts = bas_str.split('-')
        start = parts[0].strip()
        end = parts[1].strip()
        if 'x' in start.lower() or 'x' in end.lower():
            start_num = int(start.lower().replace('x', '0'))
            end_num_str = end.lower().replace('x', '9')
            for a in range(start_num, int(end_num_str) + 1):
                accounts.append(a)
        else:
            for a in range(int(start), int(end) + 1):
                accounts.append(a)
    elif 'x' in bas_str.lower():
        base = int(bas_str.lower().replace('x', '0'))
        for i in range(10):
            accounts.append(base + i)
    else:
        try:
            accounts.append(int(bas_str))
        except ValueError:
            pass
    return sorted(set(accounts))


def compress_account_codes(accounts):
    """Compress account codes into wildcard patterns for MIS Builder.
    
    MIS Builder supports %% wildcards in bal[] expressions.
    Consecutive full hundred-blocks are compressed:
      [3000, 3001, ..., 3099] → ['30%%']
      [3000, 3001, ..., 3799] → ['30%%', '31%%', ..., '37%%']
    
    This dramatically reduces expression size and SQL query complexity
    (from 800 OR conditions to 8 LIKE conditions).
    """
    if not accounts:
        return ''
    # Group by first 2 digits (hundreds block)
    from collections import defaultdict
    groups = defaultdict(list)
    for acc in accounts:
        prefix = str(acc)[:2]
        groups[prefix].append(acc)
    
    result = []
    for prefix in sorted(groups.keys()):
        codes = sorted(groups[prefix])
        n = len(codes)
        lo, hi = min(codes), max(codes)
        base = int(prefix + '00')
        # Check if this group covers the full hundred-block (XX00-XX99)
        # so wildcards are safe (won't match unintended accounts)
        full_block = (n == 100 and lo == base and hi == base + 99)
        near_full = (n >= 90 and lo == base and hi == base + 99)
        if full_block or near_full:
            result.append(f'{prefix}%%')
        else:
            # Small/specific range: keep individual codes
            for c in codes:
                result.append(str(c))
    return ', '.join(result)


def format_bal_expression(accounts, negate=False):
    """Skapa MIS bal[]-uttryck från kontonummer.
    Uses wildcard compression for performance."""
    if not accounts:
        return ''
    compressed = compress_account_codes(accounts)
    expr = 'bal[' + compressed + ']'
    if negate:
        expr += ' * -1'
    return expr


def extract_bas_accounts(sh, row_num):
    """Hitta BAS-kontoreferenser i en rad.
    BAS-referenser finns som grupper av 3 kolumner:
      Col C: 'BAS' (Utgivare)
      Col C+1: 'BAS-konto' (Namn)
      Col C+2: kontorangen (Nummer), t.ex. '191x-198x'
    """
    accounts = []
    max_col = min(sh.max_column + 1, 250)
    for c in range(20, max_col - 2):
        val_c = str(sh.cell(row_num, c).value or '')
        val_c1 = str(sh.cell(row_num, c + 1).value or '')
        if val_c == 'BAS' and 'BAS-konto' in val_c1:
            num_val = str(sh.cell(row_num, c + 2).value or '')
            if num_val:
                accounts.extend(expand_bas_range(num_val))
    return sorted(set(accounts))


def get_display_name(sh, row_num):
    """Hämta det svenska visningsnamnet för en KPI."""
    for c in [8, 7, 6, 5]:
        val = sh.cell(row_num, c).value
        if val and str(val).strip():
            return str(val).strip()
    return ''


def get_hierarchy_level(sh, row_num):
    """Bestäm hierarkinivå baserat på display-kolumner (E=5, F=6, G=7, H=8).
    Returnerar (level, display_text) där level 0=mest yttre, 3=innersta."""
    for c in [5, 6, 7, 8]:
        val = sh.cell(row_num, c).value
        if val and str(val).strip():
            return (c - 5, str(val).strip())
    return (None, '')


def generate_styles_xml():
    """Generera standard 5-stilars XML för K2/K3 rapporter."""
    return '''        <record id="report_style_k2_1" model="mis.report.style">
            <field name="name">Style for money K2</field>
            <field eval="False" name="prefix_inherit"/>
            <field eval="False" name="suffix_inherit"/>
            <field name="suffix">SEK</field>
            <field eval="False" name="dp_inherit"/>
            <field name="dp">0</field>
            <field eval="False" name="indent_level_inherit"/>
            <field name="indent_level">2</field>
        </record>
        <record id="report_style_k2_2" model="mis.report.style">
            <field name="name">Style account K2</field>
            <field eval="False" name="indent_level_inherit"/>
            <field name="indent_level">4</field>
            <field eval="False" name="font_style_inherit"/>
            <field name="font_style">italic</field>
            <field eval="False" name="prefix_inherit"/>
            <field eval="False" name="suffix_inherit"/>
            <field name="suffix">SEK</field>
        </record>
        <record id="report_style_k2_3" model="mis.report.style">
            <field name="name">Style total K2</field>
            <field eval="False" name="background_color_inherit"/>
            <field name="background_color">#967C8B</field>
            <field eval="False" name="color_inherit"/>
            <field name="color">#FFFFFF</field>
            <field eval="False" name="font_weight_inherit"/>
            <field name="font_weight">bold</field>
            <field eval="False" name="prefix_inherit"/>
            <field eval="False" name="suffix_inherit"/>
            <field name="suffix">SEK</field>
        </record>
        <record id="report_style_k2_4" model="mis.report.style">
            <field name="name">Style bold K2</field>
            <field eval="False" name="font_weight_inherit"/>
            <field name="indent_level">0</field>
            <field name="font_weight">bold</field>
            <field eval="False" name="prefix_inherit"/>
            <field eval="False" name="suffix_inherit"/>
            <field name="suffix">SEK</field>
        </record>
        <record id="report_style_k2_5" model="mis.report.style">
            <field name="name">Style bold sum K2</field>
            <field eval="False" name="font_weight_inherit"/>
            <field name="indent_level">0</field>
            <field name="font_weight">bold</field>
            <field eval="False" name="font_size_inherit"/>
            <field name="font_size">medium</field>
            <field eval="False" name="prefix_inherit"/>
            <field name="suffix">SEK</field>
        </record>'''


def generate_report_xml(sheet_def, compact=False):
    """Generera XML för en rapport.
    compact=True: utelämnar auto_expand_accounts (inga kontokolumner)."""
    excel_path = sheet_def['excel_path']
    wb = load_workbook(excel_path)
    sh = wb[sheet_def['sheet']]
    report_id = sheet_def['report_id']
    if compact:
        report_id += '_compact'
    report_name = sheet_def['report_name']
    if compact:
        report_name += ' (kompakt)'
    elem_col = sheet_def['elem_col']
    abstract_col = sheet_def['abstract_col']
    saldo_col = sheet_def['saldo_col']

    lines = []
    seq_counter = [0]

    def next_seq():
        seq_counter[0] += 1
        return seq_counter[0]

    # ── Collect all rows with hierarchy info ────────────────────────────────
    rows_data = []
    for r in range(2, sh.max_row + 1):
        elem = sh.cell(r, elem_col).value
        if elem and str(elem).strip():
            abstract = str(sh.cell(r, abstract_col).value or '').lower() == 'true'
            saldo = str(sh.cell(r, saldo_col).value or '')
            display = get_display_name(sh, r)
            level, level_text = get_hierarchy_level(sh, r)
            accounts = extract_bas_accounts(sh, r)
            negate = saldo == 'credit'
            is_sum = 'Summa' in display or elem.startswith('Summa')

            rows_data.append({
                'row': r,
                'elem': str(elem).strip(),
                'abstract': abstract,
                'saldo': saldo,
                'display': display,
                'level': level,
                'level_text': level_text,
                'accounts': accounts,
                'negate': negate,
                'is_sum': is_sum,
            })

    # ── Build hierarchy tree ────────────────────────────────────────────────
    for i, rd in enumerate(rows_data):
        parent = None
        level = rd['level']
        if level is not None:
            for j in range(i - 1, -1, -1):
                prev = rows_data[j]
                prev_level = prev['level']
                if prev_level is not None and prev_level < level:
                    parent = prev
                    break
        rd['parent'] = parent

    # ── Second pass: for KPIs without own accounts, aggregate from section scope
    # A KPI at level N should collect all accounts from KPIs between
    # the preceding KPI at a strictly lower level and itself (exclusive).
    for i, rd in enumerate(rows_data):
        if rd['accounts']:
            continue  # Already has accounts from taxonomy
        if rd['abstract']:
            continue  # Abstract headers don't need accounts
        if rd['level'] is None:
            continue  # No hierarchy info, can't determine section
        # Find section start: the preceding KPI at a strictly lower level
        section_start = 0
        kpi_level = rd['level']
        for j in range(i - 1, -1, -1):
            prev = rows_data[j]
            prev_level = prev['level']
            if prev_level is not None and prev_level < kpi_level:
                section_start = j + 1
                break
        # Collect all accounts from section children
        child_accounts = set()
        for j in range(section_start, i):
            child = rows_data[j]
            if child['accounts']:
                child_accounts.update(child['accounts'])
        if child_accounts:
            rd['accounts'] = sorted(child_accounts)
            if rd['elem'] in ASSET_SUM_KPIS:
                rd['negate'] = False  # Assets are debit
            elif rd['elem'] in LIABILITY_SUM_KPIS:
                rd['negate'] = True  # Liabilities/equity/income are credit

    # ─── Report record ─────────────────────────────────────────────────────
    lines.append(f'''        <record id="{report_id}" model="mis.report">
            <field name="name">{report_name}</field>
        </record>''')

    # ─── KPI records ──────────────────────────────────────────────────────
    for rd in rows_data:
        seq = next_seq()
        elem = rd['elem']
        is_abstract = rd['abstract']
        display = rd['display'] or elem
        kpi_id = f"{report_id}_{elem}"

        is_sum = rd['is_sum']

        if is_abstract and is_sum:
            style = 'report_style_k2_5'
        elif is_abstract:
            style = 'report_style_k2_4'
        else:
            style = 'report_style_k2_1'

        type_field = ''
        budgetable = 'True'
        if is_abstract and not is_sum:
            type_field = '\n            <field name="type">str</field>'
            budgetable = 'False'
        elif is_sum:
            type_field = '\n            <field name="type">num</field>'
            budgetable = 'False'

        auto_expand = ''
        auto_style = ''
        if not compact and not is_abstract and not is_sum:
            auto_expand = '\n            <field name="auto_expand_accounts">True</field>'
            auto_style = '\n            <field name="auto_expand_accounts_style_id" ref="report_style_k2_2"/>'

        lines.append(f'''        <record id="{kpi_id}" model="mis.report.kpi">
            <field name="report_id" ref="{report_id}"/>
            <field name="name">{elem}</field>
            <field name="description">{display}</field>
            <field name="style_id" ref="{style}"/>
            <field name="sequence">{seq}</field>{type_field}
            <field name="budgetable">{budgetable}</field>{auto_expand}{auto_style}
        </record>''')

        accounts = rd['accounts']
        if accounts:
            bal_expr = format_bal_expression(accounts, rd['negate'])
            expr_id = f"kpi_{kpi_id}"
            lines.append(f'''        <record id="{expr_id}" model="mis.report.kpi.expression">
            <field name="kpi_id" ref="{kpi_id}"/>
            <field name="name">{bal_expr}</field>
        </record>''')

    wb.close()
    return '\n'.join(lines)


def write_xml(filename, output_dir, styles_xml, report_xml):
    """Write one XML file with styles + report data."""
    full_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
{styles_xml}

{report_xml}
    </data>
</odoo>'''
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_xml)
    return os.path.getsize(filepath)


def generate_all(sheets, output_dir):
    """Generera alla XML-filer för en uppsättning SHEETS-definitioner."""
    print("Generating MIS XML files from Excel taxonomy...")
    styles_xml = generate_styles_xml()
    for sd in sheets:
        print(f"  Processing sheet: {sd['sheet']}...")
        report_xml = generate_report_xml(sd, compact=False)
        size = write_xml(sd['filename'], output_dir, styles_xml, report_xml)
        print(f"    → Full: {sd['filename']} ({size} bytes)")
        report_xml_compact = generate_report_xml(sd, compact=True)
        size_c = write_xml(sd['filename_compact'], output_dir, styles_xml, report_xml_compact)
        print(f"    → Compact: {sd['filename_compact']} ({size_c} bytes)")
    print("\nDone!")
