{
    'name': 'l10n_se: Tax Display Name',
    'version': '18.0.1.0.0',
    'summary': 'Show tax description instead of name in selection fields and dropdowns',
    'category': 'Accounting/Localizations',
    'description': """
        Overrides the tax display name logic to show the tax description
        (plain text, stripped of HTML) when available, falling back to
        the tax name when no description is set. Affects all many2one
        dropdowns, search results, and any other field relying on display_name.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/l10n_se_tax_display_name',
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
}