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
    'name': 'l10n_se: Accounting Year End Reports',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Sweden - Accounting Year End Reports',
    'category': 'Accounting',
    'description': """
Swedish accounting Year End Reports
===================================
http://www.srfredovisning.se/srf-mallar-for-arsredovisning-2/2-exempel/
http://www.srfredovisning.se/foretagsanalys-med-redovisningsinformation/3-analys-med-nyckeltal/
http://www.srfredovisning.se/foretagsanalys-med-redovisningsinformation/4-analys-med-kassafloden/

     """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_yearend_report',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'depends': ['l10n_se_tax_report'],
    'data': [
        'wizard/year_end_report.xml',
    ],
    'demo_xml' : [],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
