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
    'name': 'Bank Statement Import ID',
    'version': '18.0.1.0.0',
    'summary': 'Prevent duplicate bank statement imports by adding unique_import_id to CAMT parsers',
    'category': 'Accounting',
    'description': """
    Extends the CAMT bank statement import parsers to generate a unique_import_id
    for each transaction using bank-assigned references (NtryRef, AcctSvcrRef, TxId, etc.).
    This prevents the same bank file from being imported multiple times.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/bank_statement_import_id',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'depends': ['account_statement_import_camt'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
