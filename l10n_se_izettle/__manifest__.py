# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<http://vertel.se>).
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
    'name': 'iZettle Format Bank Statements Import',
    'version': '14.0.0.1.0',
    'license': 'AGPL-3',
    'author':  'Vertel AB',
    'website': 'https://vertel.se',
    'category': 'Banking addons',
    'depends': [
        'account_period', 
        'l10n_se_account_bank_statement_import', 
        'l10n_se_bank', 
        'l10n_se_account_payment_order'],
    'external_dependencies': {
        'python': ['xlrd', 'openpyxl'],
    },
    'data': ['account_reconcile_model_data.xml'],
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
