{
    'name': 'l10n_se: Currency Revaluation',
    'version': '18.0.1.0.0',
    'summary': 'Unrealised revaluation of open monetary items in foreign currency.',
    'category': 'Accounting/Localization',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_currency_revaluation',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'images': ['static/description/banner.png'],
    'description': '''
Currency Revaluation
====================

Revalues open monetary items in foreign currency at the closing rate and
posts the difference, with the reversal created at the same time.

K2 (BFNAR 2016:10) and K3 (BFNAR 2012:1, ch. 30) require monetary items in
foreign currency to be translated at the closing rate. Odoo core handles
realised differences only; the unrealised report lives in Enterprise
account_reports, which we do not run.

Only monetary items are revalued: open customer receivables and supplier
payables. Inventory, fixed assets and prepayments stay at their historical
rate.

Gains post to 3960 and losses to 7960 — the BAS mirror pair for operating
receivables and payables.

Features:

    - Extends Odoo: Builds on account.move, res.company, res.currency.rate.
    ''',
    'depends': [
        'account',
        'l10n_se_extended',
    ],
    # The chart is applied by l10n_se_extended's own post_init_hook, which
    # runs after ours because it is a dependency. The accounts are
    # therefore set lazily on first use as well — see _ensure_defaults.
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/currency_revaluation_wizard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
