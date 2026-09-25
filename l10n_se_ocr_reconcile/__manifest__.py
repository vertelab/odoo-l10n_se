{
    'name': 'Swedish OCR Bank Reconciliation',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Bridge module to match Swedish OCR numbers from bank feeds with invoices via OCA reconciliation.',
    'description': '''
Swedish OCR Bank Reconciliation
===============================

    Bridge module to match Swedish OCR numbers from bank feeds with invoices via OCA reconciliation.

    Features:

        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.bank.statement, account.bank.statement.line, account.reconcile.model.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_ocr_reconcile',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'depends': ['l10n_se_ocr', 'account_reconcile_oca', 'account'],
    'data': [
        'views/account_bank_statement_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
