# -*- coding: utf-8 -*-
{
    'name': 'l10n_se: Default K3 Chart of Accounts',
    'version': '18.0.1.1.0',
    'summary': 'Satt BAS K3-kontoplan som standard for svenska foretag.',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_default_k3',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': '''
Default K3 Chart of Accounts
============================

Odoo 18:s inbyggda l10n_se registrerar se_K3 (BAS komplett K3),
men ingenting satter den som default. Ett nytt foretag med land SE far
generic_coa (51 engelska konton) i stallet for BAS K3-plan
(1201 svenska BAS-konton, inkl. uppskjuten skatt 1370/2240/2250 och
K3:s eget kapital-fonder 2082/2085/2087/2089/2096/2097).

Samma logik som l10n_se_default_k2, men for K3-regelverket
(BFNAR 2012:1). Anvand den har modulen i stallet for l10n_se_default_k2
i bolag som tillampar K3 - de tva ar alternativa, inte komplementara.

Modulen ar idempotent och ror aldrig ett foretag som redan har en
kontoplan med bokforingsposter.
''',
    'depends': ['l10n_se', 'l10n_se_extended'],
    'data': ['data/cron_data.xml'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
