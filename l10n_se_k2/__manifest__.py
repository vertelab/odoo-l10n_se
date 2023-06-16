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
    'name': 'l10n_se: Swedish K2 Accounts',
    'version': '16.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'A list of Swedish Municipalities',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_k2',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    #'images': ['static/description/banner.png'], # 560x280 px.
    'depends': ['l10n_se'],
    'data': [
        'data/k2_account_chart_template.xml',
        'views/view_account_chart_template_form.xml',
        'views/account_chart_template_server_action.xml',
    ],
    'demo': [
    ],
    'installable': 'True',
}
