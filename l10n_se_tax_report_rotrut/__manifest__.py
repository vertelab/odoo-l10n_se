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
    #'images': ['images/main_screenshot.png'],
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/',
    'license': 'AGPL-3',
    'depends': ['l10n_se', 'hr', 'account', 'sales_team'],
    'data': [
        'data/account.xml',
        'data/skv_code.xml',
        'views/account_rotrut_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': False,
    'installable': True,    
    'auto_install': False,
}
