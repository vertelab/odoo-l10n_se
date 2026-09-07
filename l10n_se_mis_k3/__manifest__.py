# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
    'version': '1.0',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Swedish MIS-reports for Aktiebolag enligt K3 (BFNAR 2012:1)',
    'category': 'Accounting/Localizations',
    'description': """
        K3-variant av svenska MIS-rapporter för aktiebolag.
        Baserad på l10n_se_mis men anpassad för K3-regelverket (BFNAR 2012:1).
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_mis_k3',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_Se',
    'images': ['static/description/banner.png'],
    'depends': ['mis_builder', 'mis_builder_budget', 'l10n_se_mis'],
    'external_dependencies': {
        'python': ['xlrd'],
    },
    'data': [
        'security/security.xml',
        'data/mis_balansrakning_k3.xml',
        'data/mis_balansrakning_k3_compact.xml',
        'data/mis_balansrakning_forkortad_k3.xml',
        'data/mis_balansrakning_forkortad_k3_compact.xml',
        'data/mis_resultatrakning_kostnadsslag_k3.xml',
        'data/mis_resultatrakning_kostnadsslag_k3_compact.xml',
        'data/mis_resultatrakning_kostnadsslag_forkortad_k3.xml',
        'data/mis_resultatrakning_kostnadsslag_forkortad_k3_compact.xml',
        'data/mis_resultatrakning_funktion_k3.xml',
        'data/mis_resultatrakning_funktion_k3_compact.xml',
        'data/mis_resultatrakning_funktion_forkortad_k3.xml',
        'data/mis_resultatrakning_funktion_forkortad_k3_compact.xml',
        'data/mis_kassaflodesanalys_k3.xml',
        'data/mis_kassaflodesanalys_k3_compact.xml',
        'data/mis_eget_kapital_k3.xml',
        'data/mis_eget_kapital_k3_compact.xml',
    ],
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
