{
    'name': 'l10n_se Date Ranges',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Provides fiscal year, quarter, and month date range types for Swedish localization.',
    'description': 'Creates date range types for fiscal year, quarter, and month.',
    'author': 'Vertel Sverige AB',
    'website': 'vertel.se',
    'license': 'AGPL-3',
    'depends': ['date_range'],
    'data': [
        'data/date_range_type_data.xml',
    ],
    'post_init_hook': '_generate_swedish_date_ranges',
    'installable': True,
    'application': False,
}
