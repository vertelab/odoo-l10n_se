# -*- coding: utf-8 -*-
{
    'name': 'l10n_se: Default K2 Chart of Accounts',
    'version': '18.0.1.0.0',
    'summary': 'Satt Vertels K2-kontoplan som standard for svenska foretag.',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_default_k2',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': '''
Default K2 Chart of Accounts
============================

l10n_se_extended registrerar extended_se_K2 via @template-dekoratorn,
men ingenting satte den som default. Ett nytt foretag med land SE fick
generic_coa (52 engelska konton) i stallet for Vertels K2-plan
(1192 svenska BAS-konton).

Den har modulen gor samma sak som l10n_se_extended:s post_init_hook,
men for databaser dar l10n_se_extended redan ar installerad.

Modulen ar idempotent och ror aldrig ett foretag som redan har en
kontoplan med bokforingsposter.
''',
    'depends': ['l10n_se_extended'],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
