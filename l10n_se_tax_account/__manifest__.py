# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) {year} {company} info@vertel.se
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
#
# https://www.odoo.com/documentation/14.0/reference/module.html
#
{
    'name': 'l10n_se: Tax Account',
    'version': '18.0.2.0.0',
    'summary': 'Sweden - Tax Account Reconciliation (Skattekontoavst\u00e4mning)',
    'category': 'Accounting',
    'description': """
Swedish Tax Account Reconciliation (Skattekontoavst\u00e4mning)
===========================================================

Fetches transactions from Skatteverket's Tax Account API and provides
a two-column reconciliation view (inspired by Fortnox, Visma, and
Business Central) for matching booked tax transactions against
official tax account records.

Features:
- Fetch tax account transactions via Skatteverket API
- Two-column reconciliation view (booked vs imported)
- Auto-matching by amount with configurable date tolerance
- Settlement journal creation on the VAT journal
- Tax account balance display and verification
- OCA reconciliation engine integration
- Batch reconciliation (massavst\u00e4mning) for past periods
- Company-level API configuration via res.config.settings
- Daily cron for automatic transaction fetching

Configuration:
- Accounting \u2192 Configuration \u2192 Settings \u2192 Skatteverket API
- Requires a certificate uploaded on the Skatteverket partner


External Dependencies:
- requests (HTTP client for SKV API)
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_tax_account',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'depends': [
        'account',
        'contacts',
        'l10n_se_tax_report',
        'account_reconcile_oca',
        'account_statement_reconcile_status',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
        'views/partner_views.xml',
        'views/journal_views.xml',
        'views/tax_account_reconciliation_views.xml',
        'wizard/tax_account_transaction_wizard_views.xml',
        'data/cron_data.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': True,
}
