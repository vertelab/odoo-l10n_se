#!/usr/bin/env python3
"""
Generator: Läser K2 Handelsbolag-taxonomi Excel och genererar MIS XML datafiler.
Kör: python3 bin/generate_mis_xml.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'l10n_se_mis'))
from mis_generator_base import generate_all

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          'k2-hb-kb-arsredovisning-2024-09-12_rev20250312_sv.xlsx')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SHEETS = [
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Balansräkning',
        'report_id': 'report_br_hbkb_k2',
        'report_name': 'Balansräkning K2',
        'filename': 'mis_balansrakning_k2.xml',
        'filename_compact': 'mis_balansrakning_k2_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förkortad balansräkning',
        'report_id': 'report_br_hbkb_forkortad_k2',
        'report_name': 'Förkortad balansräkning K2',
        'filename': 'mis_balansrakning_forkortad_k2.xml',
        'filename_compact': 'mis_balansrakning_forkortad_k2_compact.xml',
        'elem_col': 10, 'abstract_col': 13, 'saldo_col': 15,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Kostnadsslagsindelad resultatr',
        'report_id': 'report_rr_hbkb_kostnadsslag_k2',
        'report_name': 'Resultaträkning kostnadsslagsindelad K2',
        'filename': 'mis_resultatrakning_kostnadsslag_k2.xml',
        'filename_compact': 'mis_resultatrakning_kostnadsslag_k2_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Förkortad kostnadsslagsindelad',
        'report_id': 'report_rr_hbkb_kostnadsslag_forkortad_k2',
        'report_name': 'Förkortad resultaträkning kostnadsslagsindelad K2',
        'filename': 'mis_resultatrakning_kostnadsslag_forkortad_k2.xml',
        'filename_compact': 'mis_resultatrakning_kostnadsslag_forkortad_k2_compact.xml',
        'elem_col': 8, 'abstract_col': 11, 'saldo_col': 13,
    },
    {
        'excel_path': EXCEL_PATH,
        'sheet': 'Kassaflödesanalys indirekt met',
        'report_id': 'report_kf_hbkb_indirekt_k2',
        'report_name': 'Kassaflödesanalys indirekt metod K2',
        'filename': 'mis_kassaflodesanalys_k2.xml',
        'filename_compact': 'mis_kassaflodesanalys_k2_compact.xml',
        'elem_col': 9, 'abstract_col': 12, 'saldo_col': 14,
    },
]

if __name__ == '__main__':
    generate_all(SHEETS, OUTPUT_DIR)
