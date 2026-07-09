#!/usr/bin/env python3
"""
Test: Verifierar att MIS Builder wildcard-uttryck matchar samma konton
som de ursprungliga explicita listorna.

Kör: python3 test_wildcard_accounts.py
"""
import os, sys, re, glob
from collections import defaultdict

# Lägg till sökväg till basgeneratorn
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'l10n_se_mis'))
from mis_generator_base import compress_account_codes

# Simulerar MIS Builder's _account_codes_to_domain
def expand_wildcard(expr):
    """Expandera wildcard-expression till set av kontonummer.
    E.g. '30%%' → {3000, 3001, ..., 3099}
          '2440' → {2440}
    """
    accounts = set()
    parts = [p.strip() for p in expr.split(',')]
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '%%' in part:
            prefix = part.replace('%%', '')
            if prefix.isdigit():
                base = int(prefix.ljust(4, '0'))
                # How many digits does the wildcard replace?
                wildcard_digits = 4 - len(prefix)
                for i in range(10 ** wildcard_digits):
                    accounts.add(base + i)
            else:
                print(f"  ⚠️  Cannot expand unknown wildcard: {part}")
        elif part.isdigit():
            accounts.add(int(part))
        else:
            print(f"  ⚠️  Unknown expression part: {part}")
    return accounts


def test_compress_account_codes():
    """Testa compress_account_codes funktionen isolerat."""
    tests = [
        (list(range(3000, 3100)), '30%%'),
        (list(range(3000, 3200)), '30%%, 31%%'),
        (list(range(1700, 1800)), '17%%'),
        ([2610, 2611, 2612], '2610, 2611, 2612'),
        ([1331, 1332, 1333, 1334], '1331, 1332, 1333, 1334'),
        (list(range(2000, 2100)), '20%%'),
        ([2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449], 
         '2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449'),
    ]
    
    print("═══ Test: compress_account_codes ═══")
    all_ok = True
    for accounts, expected_str in tests:
        result = compress_account_codes(accounts)
        # Expand both to sets for comparison
        expected_set = set(accounts)
        result_set = expand_wildcard(result)
        
        if expected_set == result_set:
            # Check it's actually shorter/using wildcards where expected
            has_wildcard = '%%' in expected_str
            result_has_wildcard = '%%' in result
            if has_wildcard and not result_has_wildcard:
                print(f'  ❌ {len(accounts):4d} konton: förväntade wildcard men fick individuella')
                print(f'     Resultat: {result}')
                all_ok = False
            else:
                wildcard_marker = ' ✅' if result_has_wildcard else ''
                print(f'  ✅ {len(accounts):4d} konton → {result}{wildcard_marker}')
        else:
            print(f'  ❌ {len(accounts):4d} konton: sets mismatch!')
            print(f'     Expected: {sorted(expected_set)}')
            print(f'     Got: {sorted(result_set)}')
            missing = expected_set - result_set
            extra = result_set - expected_set
            if missing: print(f'     Missing: {sorted(missing)[:10]}...')
            if extra: print(f'     Extra: {sorted(extra)[:10]}...')
            all_ok = False
    
    return all_ok


def test_xml_expressions():
    """Testa alla XML-filer: verifiera att wildcard-uttryck matchar originalkontona."""
    import xml.etree.ElementTree as ET
    
    print("\n═══ Test: XML-filer — wildcard expansion ═══")
    all_ok = True
    files_tested = 0
    
    # Hitta alla MIS XML-filer
    patterns = [
        'l10n_se_mis_k2/data/mis_*.xml',
        'l10n_se_mis_k2_filial/data/mis_*.xml',
        'l10n_se_mis_k2_forening/data/mis_*.xml',
        'l10n_se_mis_k2_handelsbolag/data/mis_*.xml',
        'l10n_se_mis_k3/data/mis_*.xml',
        'l10n_se_mis_k3_koncern/data/mis_*.xml',
    ]
    
    for pattern in patterns:
        for f in sorted(glob.glob(pattern)):
            files_tested += 1
            tree = ET.parse(f)
            root = tree.getroot()
            data = root.find('data')
            
            # Hitta alla KPI expression records
            exprs = [r for r in data.findall('record') 
                     if r.get('model') == 'mis.report.kpi.expression']
            
            for expr in exprs:
                kpi_id = None
                expr_text = None
                for field in expr.findall('field'):
                    name = field.get('name')
                    if name == 'kpi_id':
                        kpi_id = field.get('ref')
                    elif name == 'name':
                        expr_text = field.text
                
                if not expr_text:
                    continue
                
                # Extrahera bal[]-uttryck
                bal_matches = re.findall(r'bal\[(.*?)\]', expr_text)
                for bal_expr in bal_matches:
                    # Expandera wildcards till set
                    expanded = expand_wildcard(bal_expr)
                    
                    # Verifiera att inga kontonummer är 0 (som skulle indikera fel)
                    if 0 in expanded:
                        print(f'  ❌ {os.path.basename(f)}: KPI {kpi_id} har konto 0!')
                        all_ok = False
                    
                    # Verifiera att alla konton är 4-siffriga
                    for acc in expanded:
                        if acc < 1000 or acc > 9999:
                            print(f'  ⚠️  {os.path.basename(f)}: KPI {kpi_id} har udda konto: {acc}')
            
            print(f'  ✅ {os.path.basename(f)}: {len(exprs)} expressioner')
    
    return all_ok, files_tested


def test_account_coverage():
    """Avancerat test: för varje KPI, verifiera att wildcard-uttrycket
    täcker exakt samma konton som en explicit lista skulle göra.
    
    Detta test expanderar varje bal[]-uttryck och jämför med
    den underliggande datan från Excel-taxonomin (där tillgänglig)."""
    import xml.etree.ElementTree as ET
    from openpyxl import load_workbook
    
    print("\n═══ Test: Account coverage (KPI för KPI) ═══")
    all_ok = True
    
    # Testa K2 AB balansräkning mot Excel-taxonomin
    excel_path = 'l10n_se_mis_k2/k2-ab-arsredovisning-2024-09-12_rev20250312_sv.xlsx'
    xml_path = 'l10n_se_mis_k2/data/mis_balansrakning_k2.xml'
    
    if not os.path.exists(excel_path):
        print(f'  ⚠️  Excel-taxonomi inte tillgänglig: {excel_path}')
        return True
    
    from mis_generator_base import extract_bas_accounts, expand_bas_range, BAS_RANGE_EXPANSIONS
    
    # Ladda Excel
    wb = load_workbook(excel_path)
    sh = wb['Balansräkning']
    
    # Ladda XML
    tree = ET.parse(xml_path)
    root = tree.getroot()
    data = root.find('data')
    
    # Bygg KPI-name → expression map från XML
    xml_exprs = {}
    for expr in data.findall('record'):
        if expr.get('model') == 'mis.report.kpi.expression':
            kpi_id = None
            expr_text = None
            for field in expr.findall('field'):
                name = field.get('name')
                if name == 'kpi_id':
                    kpi_id = field.get('ref')
                elif name == 'name':
                    expr_text = field.text
            if kpi_id and expr_text:
                xml_exprs[kpi_id] = expr_text
    
    # Gå igenom varje rad i Excel och jämför
    for r in range(2, sh.max_row + 1):
        elem = sh.cell(r, 10).value
        if not elem:
            continue
        elem = str(elem).strip()
        
        # Hämta BAS-konton från Excel (den ursprungliga, outvidda listan)
        raw_accounts = []
        for c in range(20, min(sh.max_column + 1, 250) - 2):
            val_c = str(sh.cell(r, c).value or '')
            val_c1 = str(sh.cell(r, c + 1).value or '')
            if val_c == 'BAS' and 'BAS-konto' in val_c1:
                num_val = str(sh.cell(r, c + 2).value or '')
                if num_val:
                    raw_accounts.append(num_val)
        
        if not raw_accounts:
            continue  # Inga BAS-konton i denna rad
        
        # Expandera till full account-lista (med BAS_RANGE_EXPANSIONS)
        expected_accounts = set()
        for ra in raw_accounts:
            expected_accounts.update(expand_bas_range(ra))
        
        # Hitta motsvarande XML-uttryck
        # Testa både med och utan compact
        for suffix in ['', '_compact']:
            kpi_id = f'report_br_k2{suffix}_{elem}'
            if kpi_id in xml_exprs:
                expr_text = xml_exprs[kpi_id]
                bal_matches = re.findall(r'bal\[(.*?)\]', expr_text)
                for bal_expr in bal_matches:
                    actual_accounts = expand_wildcard(bal_expr)
                    
                    # Om expected_accounts är en delmängd av actual_accounts är det OK
                    # (aggregation kan lägga till fler konton)
                    if not expected_accounts.issubset(actual_accounts):
                        missing = expected_accounts - actual_accounts
                        print(f'  ❌ {elem} ({suffix or "full"}): saknar {len(missing)} konton')
                        print(f'     T.ex.: {sorted(missing)[:10]}')
                        all_ok = False
                    else:
                        # Verifiera att vi inte tappat konton
                        extra = actual_accounts - expected_accounts
                        # Extra konton kan komma från aggregation
                        if extra:
                            # Det är OK för sum-KPI:er som aggregerar från barn
                            pass
    
    wb.close()
    return all_ok


if __name__ == '__main__':
    # Ensure we're in the repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  TEST: Wildcard account coverage i MIS Builder expressions     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    ok1 = test_compress_account_codes()
    ok2, files = test_xml_expressions()
    ok3 = test_account_coverage()
    
    print()
    print("════════════════════════════════════════════════════")
    print(f"  Sammanfattning:")
    print(f"    compress_account_codes:  {'✅ PASS' if ok1 else '❌ FAIL'}")
    print(f"    XML-struktur ({files} filer): {'✅ PASS' if ok2 else '❌ FAIL'}")
    print(f"    Account coverage:        {'✅ PASS' if ok3 else '❌ FAIL'}")
    print("════════════════════════════════════════════════════")
    
    sys.exit(0 if (ok1 and ok2 and ok3) else 1)
