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
    'name': 'l10n_se: Tax Reconcile API',
    'summary': 'Implementing Skatteverkets API',
    'author': 'Vertel AB',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'category': 'Accounting',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-l10n-se/l10n-se-tax-reconcile-api',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'description': """Implementing Skatteverkets API


     """,
    'depends': ['account','account_period', 'l10n_se','account_statement_import'],
    'init_xml': [],
    'data': [
        #'data/load_account_chart_template_data.xml',
        'wizard/load_mynt_view.xml',
        'security/ir.model.access.csv',

    ],
    'demo': [
        #'demo/load_account_chart_template_data.xml',
    ],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
