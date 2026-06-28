# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

{
    'name': 'l10n_se: Swedish Accounting Training (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish accounting education — system-independent theory with Odoo practice guides',
    'category': 'Accounting/Training',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_account_lms',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish Accounting LMS (l10n_se_account_lms)
============================================
System-independent training in Swedish accounting concepts and procedures,
with Odoo-specific practice guides.

Content structured around Swedish accounting standards (BAS, BFNAR, K2/K3)
and Skatteverket's reporting requirements.

Topics covered:
- Grundläggande bokföring (Basic accounting principles)
- Kundreskontra & Leverantörsreskontra (AR/AP ledgers)
- Bankavstämning (Bank reconciliation)
- Momsredovisning (VAT declaration)
- Arbetsgivardeklaration AGI (Employer declaration)
- Periodisk sammanställning (EU sales listing)
- Bokslut & Årsredovisning (Year-end closing & annual report)
- SIE import/export
- Skattekontoavstämning (Tax account reconciliation)

Sources: Skatteverket, FAR, Xpectum, Bokföringstips.se
    """,
    'depends': [
        'l10n_se_extended',
        'l10n_se_tax_report',
        'hr',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/training_categories.xml',
        'data/training_lessons_basics.xml',
        'data/training_lessons_vat.xml',
        'data/training_lessons_reconciliation.xml',
        'data/training_lessons_year_end.xml',
        'views/training_category_views.xml',
        'views/training_lesson_views.xml',
        'views/training_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
