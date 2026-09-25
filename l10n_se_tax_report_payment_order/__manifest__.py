# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'l10n_se: Tax Report Payment Order',
    'version': '18.0.1.0.0',
    'summary': 'Payment order support for tax declarations.',
    'description': '''
Tax Report Payment Order
========================

    Payment order support for tax declarations.

    Features:

        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.declaration.
    ''',
    'category': 'Accounting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_tax_report_payment_order',
    'license': 'AGPL-3',
    'depends': [
        'l10n_se_tax_report',
        'account_payment_order',
    ],
    'data': [
        'views/declaration_payment_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
