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
    'name': 'l10n_se: BgMax Format Bank Statements Import',
    'summary': 'Reading BgMax formated files from Bankgirocentralen.',
    'author': 'Vertel AB',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'category': 'Accounting',
    'version': '14.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/l10n_se',
    'description': """
        Reading BgMax formated files from Bankgirocentralen.

        There are some problems with the OCA class AcountBankStatementImport
        from OCA bank-statement-import/account_bank_statement_import/models/account_bank_statement_import.py
        change pop to get:

        140,141c140,141
<         currency_code = stmt_vals.pop('currency_code')
<         account_number = stmt_vals.pop('account_number')
---
>         currency_code = stmt_vals.get('currency_code')
>         account_number = stmt_vals.get('account_number')
328c328
<         for line_vals in stmt_vals['transactions']:
---
>         for line_vals in stmt_vals.get('transactions',[]):
380c380
<         for line_vals in stmt_vals['transactions']:
---
>         for line_vals in stmt_vals.get('transactions',[]):


        """,
    'depends': ['l10n_se_account_bank_statement_import', 'l10n_se_bank', 'l10n_se_account_payment_order'],
    'data': [
        'account_bank_statement_data.xml',
        'account_bank_statement_view.xml',
    ],
    'summary': 'BgMax Format Bank Statements Import',
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
