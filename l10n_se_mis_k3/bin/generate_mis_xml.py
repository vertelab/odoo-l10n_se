#!/usr/bin/env python3
"""
Generator: Läser K3 AB-taxonomi Excel och genererar MIS XML datafiler.
Kör: python3 bin/generate_mis_xml.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'l10n_se_mis'))
from mis_generator_base import generate_all

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          'k3-ab-arsredovisning-2021-10-31-rev20241120.xlsx')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SHEETS = [
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Balansräkning',
        'report_id': 'report_br_k3',
        'report_name': 'Balansräkning K3',
        'filename': 'mis_balansrakning_k3.xml',
        'filename_compact': 'mis_balansrakning_k3_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förkortad balansräkning',
        'report_id': 'report_br_forkortad_k3',
        'report_name': 'Förkortad balansräkning K3',
        'filename': 'mis_balansrakning_forkortad_k3.xml',
        'filename_compact': 'mis_balansrakning_forkortad_k3_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Kostnadsslagsindelad resultatr',
        'report_id': 'report_rr_kostnadsslag_k3',
        'report_name': 'Resultaträkning kostnadsslagsindelad K3',
        'filename': 'mis_resultatrakning_kostnadsslag_k3.xml',
        'filename_compact': 'mis_resultatrakning_kostnadsslag_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förkortad kostnadsslagsindelad',
        'report_id': 'report_rr_kostnadsslag_forkortad_k3',
        'report_name': 'Förkortad resultaträkning kostnadsslagsindelad K3',
        'filename': 'mis_resultatrakning_kostnadsslag_forkortad_k3.xml',
        'filename_compact': 'mis_resultatrakning_kostnadsslag_forkortad_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Funktionsindelad resultaträkni',
        'report_id': 'report_rr_funktion_k3',
        'report_name': 'Resultaträkning funktionsindelad K3',
        'filename': 'mis_resultatrakning_funktion_k3.xml',
        'filename_compact': 'mis_resultatrakning_funktion_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förkortad funktionsindelad res',
        'report_id': 'report_rr_funktion_forkortad_k3',
        'report_name': 'Förkortad resultaträkning funktionsindelad K3',
        'filename': 'mis_resultatrakning_funktion_forkortad_k3.xml',
        'filename_compact': 'mis_resultatrakning_funktion_forkortad_k3_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Kassaflödesanalys indirekt met',
        'report_id': 'report_kf_indirekt_k3',
        'report_name': 'Kassaflödesanalys indirekt metod K3',
        'filename': 'mis_kassaflodesanalys_k3.xml',
        'filename_compact': 'mis_kassaflodesanalys_k3_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förändringar i eget kapital',
        'report_id': 'report_equity_k3',
        'report_name': 'Förändringar i eget kapital K3',
        'filename': 'mis_eget_kapital_k3.xml',
        'filename_compact': 'mis_eget_kapital_k3_compact.xml',
        'elem_col': 11, 'abstract_col': 14, 'saldo_col': 16,
    },
]

if __name__ == '__main__':
    generate_all(SHEETS, OUTPUT_DIR)
