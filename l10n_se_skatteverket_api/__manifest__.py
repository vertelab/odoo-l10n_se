# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'l10n_se: Skatteverket API',
    'version': '18.0.1.0.0',
    'summary': 'Sweden - Shared Skatteverket API module',
    'category': 'Accounting',
    'description': """
Shared Skatteverket API authentication and helpers for
l10n_se_tax_report (VAT/PC declarations) and
l10n_se_tax_account (tax account reconciliation).

Features:
- Certificate-based OAuth2 authentication
- E-identification OAuth2 flow with callback
- Computed API URLs per service type (moms, PC, skattekonto)
- Shared helper methods for API calls
- Company-level API configuration
- SKV partner with certificate and token storage
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_skatteverket_api',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'contacts',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
}
