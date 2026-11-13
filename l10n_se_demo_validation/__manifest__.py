# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'l10n_se: Demo data validation (Swedish chart of accounts)',
    'version': '18.0.1.0.0',
    'summary': 'Guards Odoo demo data against non-Swedish chart of accounts',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_demo_validation',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish demo data validation
============================

Odoo's generic accounting demo data (``account/demo/account_demo.py``) creates
journal entries that reference generic chart-of-accounts codes (3001, 4001,
1510, ...). Those codes do not exist in the Swedish BAS charts, so the demo
loader silently drops the ``account_id`` and writes **unbalanced journal
entries** — corrupting the chart of accounts and the currency setup.

This module solves two use cases:

A. **"Load demo data" link in Settings** on a database that has no demo data.

   ``ir.demo.install_demo`` -> ``force_demo()`` loads demo data for every
   installed module. We intercept ``_get_demo_data()`` and replace the
   account-move / bank-statement / reconcile-model blocks with a Swedish
   dataset built on real BAS accounts for the company's chart template
   (extended_se / extended_se_K2 / extended_se_K3). Nothing is posted that
   refers to a non-existent account.

B. **``repo_apply`` of a demo database** (``accounting_full.repo``) that must
   end up with a Swedish K2 chart and SEK.

   The module ships a ``demo`` section that, on demo install, switches the
   main company to the Swedish K2 chart template and SEK *before* the
   accounting demo data is generated. The generic demo data is then replaced
   by the Swedish dataset from (A).

Configuration
-------------
Nothing. Install the module on any database that uses a Swedish chart
template; it is inert on other charts.
""",
    'depends': [
        'account',
        'l10n_se',
        'l10n_se_extended',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/l10n_se_demo_wizard_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company_se.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
