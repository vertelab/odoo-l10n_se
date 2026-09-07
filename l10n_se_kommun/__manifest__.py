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
    'name': 'l10n_se: Sweden Kommun - Accounting',
    'version': '1.0',
    'summary': 'Sweden Kommun - Chart of accounts',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_kommun',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'description': """
        Sweden Kommun- Chart of accounts

        * Kommun BAS 2025 (Chart of account, rules from SKV-283 v16)
        * Tax-codes from SKV-4700 r1-49  SKV-409

        Next step is to choose a chart_of_accounts and that can be done in the settings meny but you need to check "Show Full Accounting Features" on you current user.
     """,
    'depends': ['account', 'l10n_se'],
    'init_xml': [],
    'data': [
        'data/custom_address_formats.xml',
    ],
    'installable': 'True',
    'application': 'False',
    'auto_install': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
