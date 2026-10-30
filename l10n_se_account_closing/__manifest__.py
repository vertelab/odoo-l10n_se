{
    "name": "l10n_se: Account Closing",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Swedish K2 closing template for OCA account_fiscal_year_closing",
    "description": """
Swedish closing bridge for account_fiscal_year_closing
======================================================

OCA ``account_fiscal_year_closing`` ships the closing machinery — the
``account.fiscalyear.closing`` wizard, its configs, mappings and closing
types — but no Swedish templates. This module adds the K2 (BFNAR 2016:10)
template so a Swedish company can close its books without hand-building
every mapping.

Mapping groups in the K2 template
---------------------------------
- **Resultatdisposition** — moves the year's result from the P&L accounts
  (3xxx-8xxx) to 2099 *Årets resultat*, then to 2098/2091 as decided by
  the annual general meeting.
- **Periodiseringsfond** — re-instates 21xx periodisation funds against
  8811/8850.
- **Överavskrivningar** — re-instates 2150 accumulated excess depreciation
  against 8850.
- **Skatteberäkning** — books 2512 *Beräknad inkomstskatt* against
  8910 *Skatt på årets resultat*.

Ownership
---------
The generic ``account_fiscal_year_mis`` module stays localization-neutral;
all BAS account numbers live here. A company that does not use the Swedish
chart simply does not install this module.
""",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-l10n_se/l10n_se_account_closing",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_fiscal_year_closing",
        "l10n_se",
    ],
    "data": [
        "data/closing_template_k2.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
