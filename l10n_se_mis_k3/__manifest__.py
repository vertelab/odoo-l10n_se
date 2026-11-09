# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<https://vertel.se>).
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
    'name': 'l10n_se: Swedish MIS-reports K3 (Aktiebolag)',
    'version': '18.0.2.0.1',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Swedish MIS-reports for Aktiebolag enligt K3 (BFNAR 2012:1).',
    'category': 'Accounting/Localizations',
    'description': '''
Swedish MIS-reports K3 (Aktiebolag)
===================================

    K3 variant of the Swedish MIS reports for limited companies.

Based on l10n_se_mis but adapted to the K3 framework (BFNAR 2012:1).
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_mis_k3',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_Se',
    'images': ['static/description/banner.png'],
    'depends': ['account', 'account_dynamic_reports', 'l10n_se_mis'],
    'external_dependencies': {
        'python': ['xlrd'],
    },
    'data': [
        'security/security.xml',
        'data/ar_br_k3.xml',
        'data/ar_br_k3_compact.xml',
        'data/ar_br_forkortad_k3.xml',
        'data/ar_br_forkortad_k3_compact.xml',
        'data/ar_rr_kostnadsslag_k3.xml',
        'data/ar_rr_kostnadsslag_k3_compact.xml',
        'data/ar_rr_kostnadsslag_forkortad_k3.xml',
        'data/ar_rr_kostnadsslag_forkortad_k3_compact.xml',
        'data/ar_rr_funktion_k3.xml',
        'data/ar_rr_funktion_k3_compact.xml',
        'data/ar_rr_funktion_forkortad_k3.xml',
        'data/ar_rr_funktion_forkortad_k3_compact.xml',
        'data/ar_kf_indirekt_k3.xml',
        'data/ar_kf_indirekt_k3_compact.xml',
        'data/ar_equity_k3.xml',
        'data/ar_equity_k3_compact.xml',
    ],
    'installable': 'True',
    'application': 'False',
}
