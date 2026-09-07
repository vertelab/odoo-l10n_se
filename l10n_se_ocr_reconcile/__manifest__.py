{
    'name': 'Swedish OCR Bank Reconciliation',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Bridge module to match Swedish OCR numbers from bank feeds with invoices via OCA reconciliation',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/account_swedish_ocr_reconcile',
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
