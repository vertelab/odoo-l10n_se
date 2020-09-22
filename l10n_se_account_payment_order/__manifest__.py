# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018- Vertel (<http://vertel.se>).
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
    'name': 'Swedish Payment Order Configuration',
    'version': '10.0.1',
    'license': 'AGPL-3',
    'author': ' Vertel AB',
    'website': 'http://vertel.se',
    'category': 'Banking addons',
    'depends': ['account_payment_order', 'l10n_se'],
    'data': [
        'res_config_view.xml',
    ],
    'summary': 'Swedish Payment Order Configuration',
    'description': """
Configuration of account for payment order
==========================================

        """,
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
