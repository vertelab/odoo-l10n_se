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
    'name': 'l10n_se: Account Tax Report',
    'version': '18.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Sweden - Account Tax Report',
    'category': 'Accounting',
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_tax_report',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish accounting Tax Report
=============================
Adds some Swedish tax and employer reports (Momsdeklaration, Arbetsgivardeklaration)

Skatteverket API Integration
----------------------------
- Submit VAT declarations directly to Skatteverket via API
- Supports certificate (cert) and e-identification (e_id) authentication
- Test/live mode toggle with configurable endpoints
- Calendar integration showing submission deadlines

Company Settings (res.company)
-------------------------------
- vat_declaration_frequency: Declaration period (month/quarter/year)
- accounting_method: Kontantmetoden or Fakturametoden
- vat_report_template_id: MIS report template for VAT declarations (default: Momsdeklaration)
- skv_test_mode: Use Skatteverket test or production API
- skv_auth_method: Authentication method (cert/e_id)
- skv_api_url, skv_auth_url, skv_token_url: Configurable API endpoints

External Dependencies
---------------------
- workalendar: Used for Swedish public holiday calculation to correctly
  determine VAT declaration deadlines. Install: pip3 install workalendar
     """,
    'author': 'Vertel AB',

    'depends': ['account_payment_order', 'calendar', 'mis_builder','l10n_se_mis', 'account_period_vrtl'],

    'external_dependencies': {
        'python': ['workalendar'],
    },

    'data': [
        'data/account_data.xml',
        'data/cron_data.xml',
        'data/mis_report_instances.xml',
        'views/account_view.xml',
        'views/res_config_view.xml',
        'views/moms_report.xml',
        'views/periodic_compilation.xml',
        'report/report.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/mis_report_view.xml',
        'views/account_fiscalyear_views.xml',
     ],
    'demo': [
        'demo/periodic_compilation_demo.xml',
        'demo/tax_report_demo.xml',
    ],
    'installable': 'True',
}
