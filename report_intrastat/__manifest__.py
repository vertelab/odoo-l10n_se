# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2023- Vertel AB (<https://vertel.se>).
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
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'l10n_se: Intrastat Reporting',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'This module gives the details of the goods traded between the countries of European Union.',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'description': """
    This module gives the details of the goods traded between the countries of European Union.
    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/report_intrastat',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    # Any module necessary for this one to work correctly

    'depends': ['base', 'product', 'delivery', 'stock', 'sale_management', 'purchase'],
    'data': [
        'data/report_intrastat_data.xml',
        'report/report_intrastat_invoice_template.xml',
        'report/report_intrastat_report.xml',
        'security/ir.model.access.csv',
        'security/report_intrastat_security.xml',
        'views/report_intrastat_views.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
