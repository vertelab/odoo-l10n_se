# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Sweden - Account Tax Report',
    'version': '1.0',
    'category': 'Report',
    'description': """
Swedish accounting Tax Report
=============================
Taxes for financial report
     """,
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    # ~ 'depends': ['l10n_se', 'account_period', 'account_payment_order','calendar','l10n_se_hr_payroll_account', 'account','report_py3o','mis_builder'],
    'depends': ['l10n_se', 'account_period', 'account_payment_order','calendar', 'account','mis_builder'],
    'data': [
        # ~ 'data/account_data.xml',
        # ~ 'data/account_financial.xml',
        'views/account_view.xml',
        'views/res_config_view.xml',
        # ~ 'wizard/import_b_and_r_report.xml', funkar inte i 12
        # ~ 'wizard/import_bolagsverket_report.xml', funkar inte i 12
        'views/moms_report.xml',
        # ~ 'views/agd_report.xml',
        # ~ 'views/sru_report.xml',
        # ~ 'views/periodic_compilation.xml',
        'report/report.xml',
        # ~ 'account_invoice_demo.xml',
        'security/ir.model.access.csv',
        'views/mis_report_view.xml',
        'demo/account_invoice.xml',
    ],
    'demo_xml' : [
        # ~ 'demo/account_invoice.yml',
        # ~ 'demo/account_invoice.xml',
    ],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
