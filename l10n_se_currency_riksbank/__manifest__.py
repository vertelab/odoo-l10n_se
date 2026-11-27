# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'l10n_se: Currency Riksbank',
    'version': '1.0.1',
    'summary': 'Exchange rates from Sveriges Riksbank (REST API).',
    'category': 'Accounting/Localizations',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_currency_riksbank',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'images': ['static/description/icon.png'],
    'description': '''
Currency Riksbank
=================

Adds Sveriges Riksbank as a currency rate provider to the OCA module
``currency_rate_update``.

The rates are the daily SEK rates published by Riksbank on its REST API,
one series per currency (``SEKEURPMI``, ``SEKUSDPMI``, ...). This replaces
the SOAP service that the old Linserv module
``currency_rate_live_riks_bank`` used and that no longer answers.

Riksbank quotes SEK per foreign unit (11.221 SEK for one EUR).
``res.currency.rate`` stores the inverse, so every rate is inverted before
it is stored.

The API allows roughly one request every five to ten seconds, so the
provider waits between the currency series and backs off when Riksbank
answers 429 Too Many Requests.

Features:

    - Extends Odoo: res.currency.rate.provider.
    ''',
    'depends': [
        'currency_rate_update',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
