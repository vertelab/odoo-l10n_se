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
    'name': 'l10n_se: SIE-import',
    'version': "0.1',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    # 'version': '14.0.0.0.1' reimplementing  base functionality lost in the porting process.
    'summary': 'Module for importing SIE-files',
    'category': 'Accounting',
    'description': """
        The module adds support for importing and reading SIE-files (.se-files)
    """,
	 #'sequence': '1',
	'author': 'Vertel AB',
	'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_sie',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'depends': ['account_period_vrtl', 'l10n_se'],
    'data': [
		'data/l10n_se_sie_view.xml',
                'views/account_view.xml',
                'data/l10n_se_sie_data.xml',
                'data/fix_account_type_skf.xml',
                'security/ir.model.access.csv',
    ],
  
    # 'demo': ['l10n_se_sie_demo.xml'],

    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
