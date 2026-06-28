# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

{
    'name': 'l10n_se: Swedish Payroll Training (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish payroll education — system-independent theory with Odoo practice guides',
    'category': 'Payroll/Training',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_payroll_lms',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish Payroll LMS (l10n_se_payroll_lms)
=========================================
System-independent training in Swedish payroll concepts and procedures,
with Odoo-specific practice guides.

Topics covered:
- Löneadministration (Salary administration basics)
- Skattetabeller & Preliminärskatt (Tax tables & withholding)
- Semester & Semesterlöneskuld (Holiday pay & liability)
- Sjuklön, VAB & Föräldraledighet (Sick pay & parental leave)
- Kollektivavtal (Collective agreements)
- Förmåner & Löneväxling (Benefits & salary exchange)
- Arbetsgivardeklaration AGI (Employer monthly declaration)
- FORA & Tjänstepension (Pension reporting)
- Arbetsgivarintyg (Employment certificates)
- Tidrapportering & SCB (Time reporting & Statistics Sweden)

Sources: Skatteverket, Försäkringskassan, FORA, Arbetsgivarverket
    """,
    'depends': [
        'l10n_se_account_lms',
    ],
    'data': [
        'data/payroll_categories.xml',
        'data/payroll_lessons_salary.xml',
        'data/payroll_lessons_agi.xml',
        'data/payroll_lessons_benefits.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
