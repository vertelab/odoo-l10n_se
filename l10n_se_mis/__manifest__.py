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
    'name': 'l10n_se: Swedish MIS-reports',
    'version': '18.0.2.0.5',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Create Swedish MIS-reports.',
    'category': 'Accounting',
    'description': '''
Swedish MIS-reports
===================

    The module works as a base for creating Swedish MIS reports.

Balance report template: these headings contain overlapping accounts; if used,
adjust according to the applicable accounting guidelines.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_mis',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_Se',
    'images': ['static/description/banner.png'], # 560x280 px.
    'depends': ['account', 'account_dynamic_reports', 'l10n_se_tax_report'],
    'external_dependencies': {
        'python': ['xlrd'],
    },
    'data': [
        # The reports are now account.report definitions, generated from the
        # old MIS Builder data files by account_report_mis_import and reviewed
        # row by row (see the change's tasks.md section 7.10).
        'data/ar_balance_sheet.xml',
        'data/ar_profit_and_loss.xml',
        'data/ar_momsdeklaration.xml',
        # SFA runs their own VAT report, already tag-based. Kept as data so a
        # customer variant does not force the standard to change.
        'data/ar_momsdeklaration_sfa.xml',
        'views/ar_report_actions.xml',
        'security/security.xml',
    ],
    'installable': 'True',
    'application': 'False',
}
