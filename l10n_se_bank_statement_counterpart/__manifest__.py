{
    'name': 'Swedish Bank Statement Counterpart (No Suspense)',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Book imported bank statement lines directly against a real '
               'counterpart account instead of a suspense/interim account.',
    'description': '''
Swedish Bank Statement Counterpart (No Suspense)
================================================

Interim (suspense) accounts are forbidden in this accounting policy. Odoo
books every imported bank statement line against the journal's suspense
account until it is reconciled, which parks the amount on an interim
account and hides errors.

This module resolves the counterpart account at import time:

- **Incoming amounts** (positive) -> the partner's receivable account, or
  the journal's configured receivable counterpart (typically 1510).
- **Outgoing amounts** (negative) -> the partner's payable account, or the
  journal's configured payable counterpart (typically 2440).

If no counterpart can be resolved, the import fails loudly instead of
silently posting to suspense.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_bank_statement_counterpart',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'depends': [
        'account',
        'account_statement_import_base',
    ],
    'data': [
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
