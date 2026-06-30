# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

{
    'name': 'l10n_se: Migration from competitors',
    'version': '18.0.1.0.0',
    'summary': 'Migrate accounting data from Fortnox, Visma, Bokio to Odoo',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_migration',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish Competitor Migration
============================
Migrate accounting data from Swedish competitors to Odoo.

Supported sources:
- Fortnox (OAuth API)
- Visma Spiris/eEkonomi (SIE import)
- Bokio (SIE import)
- Generic SIE import (any system)

Migration wizard guides through:
1. Select source system
2. Authenticate / upload SIE file
3. Map accounts and partners
4. Import data (chart of accounts, journal entries, partners, invoices)
    """,
    'depends': [
        'l10n_se_sie',
        'l10n_se_extended',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/migration_wizard_views.xml',
        'views/migration_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
