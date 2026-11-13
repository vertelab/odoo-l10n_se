{
    'name': 'l10n_se Date Ranges',
    'version': '18.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'Swedish quarter and week date range types for account_fiscal_year_vrtl.',
    'description': '''
l10n_se Date Ranges
===================

    Swedish quarter and week date range types.

    Fiscal Year and Month are generic and live in account_fiscal_year_vrtl,
    which this module depends on. This module adds the two types whose naming
    is locale-specific: Quarter (``Q26-1``) and Week (``W2601``). It also
    generates the ranges for them on install, so a fresh database has periods
    to close immediately.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_date_ranges',
    'license': 'AGPL-3',
    'depends': ['account_fiscal_year_vrtl', 'date_range'],
    'data': [
        'data/date_range_type_data.xml',
    ],
    'post_init_hook': '_generate_swedish_date_ranges',
    'installable': True,
    'application': False,
}
