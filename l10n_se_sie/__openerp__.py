# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel (<http://www.vertel.se>).
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
    'name': 'l10n_se_sie',
    'version': '0.1',
    'category': 'Localization/Account Charts',
    'description': """ Sweden - Chart of accounts  """,
    'author': 'Vertel',
    'website': 'http://www.vertel.se',

    'depends': ['account','l10n_se'],
    'data': ['l10n_se_sie_view.xml','l10n_se_sie_period_view.xml'],
    'demo': ['l10n_se_sie_demo.xml'],

    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
