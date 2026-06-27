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
    'name': 'l10n_se: Bokslut och Årsredovisning',
    'version': '18.0.0.0.1',
    'summary': 'Sweden - Year-End Closing and Annual Report',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_bokslut',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish Year-End Closing and Annual Report
===========================================

Adds a complete year-end closing workflow for Swedish companies:
- Year-end planning with tax calculation
- Bookkeeping adjustments (non-deductible costs, non-taxable income)
- Tax calculation with full chain (result before dispositions -> taxable result -> tax)
- Closing verifications with preliminary booking support
- Checklist via Kanban board (project.task with stages)
- Milestone tracking for key closing dates
- Annual report generation (BR, RR, notes, management report)
- Periodization funds (tax allocation reserves)
- Excess depreciation (tax depreciation above book depreciation)

Integration
-----------
- Uses project.task for the closing checklist (Kanban visualization)
- Uses project.milestone for key closing milestones
- Integrates with account.sru.declaration for SRU generation
- Integrates with account.financial.report for BR/RR structure
- Integrates with l10n_se_tax_report for SKV API infrastructure

K2 and K3 rule sets supported for annual reports.
     """,
    'author': 'Vertel AB',

    'depends': [
        'l10n_se_tax_report',
        'l10n_se_mis',
        'l10n_se_account_financial_report',
        'l10n_se_extended',
        'project',
        'account_period_vrtl',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/bokslut_task_stages.xml',
        'data/bokslut_task_data.xml',
        'data/cron_data.xml',
        'views/bokslut_planning_views.xml',
        'views/bokslut_adjustment_views.xml',
        'views/project_task_views.xml',
        'views/project_project_views.xml',
        'report/annual_report_pdf.xml',
        'report/bokslut_dokumentation_pdf.xml',
    ],
    'demo': [
        'demo/bokslut_demo.xml',
    ],
    'installable': True,
}
