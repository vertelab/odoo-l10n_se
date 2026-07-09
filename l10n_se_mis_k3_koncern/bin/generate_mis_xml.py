#!/usr/bin/env python3
"""
Generator: Läser K3 Koncern-taxonomi Excel och genererar MIS XML datafiler.
Kör: python3 bin/generate_mis_xml.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'l10n_se_mis'))
from mis_generator_base import generate_all

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          'k3k-ab-arsredovisning-2021-10-31-rev20241120.xlsx')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SHEETS = [
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Koncernens kostnadsslagsindela',
        'report_id': 'report_rr_koncern_k3',
        'report_name': 'Koncernens resultaträkning kostnadsslagsindelad K3',
        'filename': 'mis_koncern_resultatrakning_kostnadsslag_k3.xml',
        'filename_compact': 'mis_koncern_resultatrakning_kostnadsslag_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Koncernens funktionsindelade r',
        'report_id': 'report_rr_koncern_funktion_k3',
        'report_name': 'Koncernens resultaträkning funktionsindelad K3',
        'filename': 'mis_koncern_resultatrakning_funktion_k3.xml',
        'filename_compact': 'mis_koncern_resultatrakning_funktion_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Koncernens balansräkning',
        'report_id': 'report_br_koncern_k3',
        'report_name': 'Koncernens balansräkning K3',
        'filename': 'mis_koncern_balansrakning_k3.xml',
        'filename_compact': 'mis_koncern_balansrakning_k3_compact.xml',
        'elem_col': 11, 'abstract_col': 14, 'saldo_col': 16,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Koncernens kassaflödesanalys i',
        'report_id': 'report_kf_koncern_k3',
        'report_name': 'Koncernens kassaflödesanalys indirekt metod K3',
        'filename': 'mis_koncern_kassaflodesanalys_k3.xml',
        'filename_compact': 'mis_koncern_kassaflodesanalys_k3_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Koncernens förändringar i eget',
        'report_id': 'report_equity_koncern_k3',
        'report_name': 'Koncernens förändringar i eget kapital K3',
        'filename': 'mis_koncern_eget_kapital_k3.xml',
        'filename_compact': 'mis_koncern_eget_kapital_k3_compact.xml',
        'elem_col': 12, 'abstract_col': 15, 'saldo_col': 17,
    },
]

if __name__ == '__main__':
    generate_all(SHEETS, OUTPUT_DIR)
