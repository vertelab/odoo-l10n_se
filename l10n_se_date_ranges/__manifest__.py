{
    'name': 'l10n_se Date Ranges',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Provides fiscal year, quarter, and month date range types for Swedish localization.',
    'description': '''
l10n_se Date Ranges
===================

    Provides fiscal year, quarter, and month date range types for Swedish localization.

    Features:

        - Extends Odoo: Builds on date.range.generator, date.range.type.
    ''',
    'description': 'Creates date range types for fiscal year, quarter, and month.',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_date_ranges',
    'license': 'AGPL-3',
    # DEPRECATED 2026-10-30: the four date.range.types and the generation
    # hook now live in l10n_se_account_fiscal_year, which depends on
    # account_fiscal_year_vrtl. Keeping both modules installable means two
    # owners of the same types and a UniqueViolation on install. Depend on
    # the bridge so an upgrade follows the new ownership.
    'depends': ['date_range', 'l10n_se_account_fiscal_year'],
    'data': [
        'data/date_range_type_data.xml',
    ],
    'post_init_hook': '_generate_swedish_date_ranges',
    'installable': False,  # DEPRECATED 2026-10-30: see l10n_se_account_fiscal_year.
    'application': False,
}
