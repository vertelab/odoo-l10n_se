# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2022 Vertel AB (<https://vertel.se>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'l10n_se: Account Tax Report Rotrut',
    'version': '14.0.0.0',
    'summary': 'Sweden - Account Tax Report Rotrut',
    'category': 'Accounting',
    'description': """
    Adds Swedish tax and employer reports (RotRut avdrag)
    """,
    'images': ['static/description/banner.png'], # 560x280 px.
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_tax_report_rotrut',
    'license': 'AGPL-3',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    # Any module necessary for this one to work correctly

    'depends': ['l10n_se', 'hr', 'account', 'sales_team'],
    'data': [
        'data/account.xml',
        'data/skv_code.xml',
        'views/account_journal_view.xml',
        'views/account_move_view.xml',
        'views/account_rotrut_view.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

