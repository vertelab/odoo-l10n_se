{
    "name": "l10n_se: Fiscal Year",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Swedish fiscal year date range types for account_fiscal_year_vrtl",
    "description": """
Swedish bridge for account_fiscal_year_vrtl
===========================================

`account_fiscal_year_vrtl` is deliberately localization-neutral: it owns the
period model, the closing logic and the hash-locking, but not the Swedish
date range *types*.

This module supplies the Swedish side:

- The four date range types (Fiscal Year, Quarter, Month, Week) with Swedish
  naming expressions (``Y2026``, ``Q26-1``, ``M2601``, ``W2601``).
- A post-init hook that generates the ranges for the previous, current and
  next year, so a fresh install has periods to close immediately.

It replaces ``l10n_se_date_ranges``, which created the same four types and
therefore collided with ``account_fiscal_year_vrtl`` on install
(``UniqueViolation`` on ``date_range_type_date_range_type_uniq``).
""",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se/apps/odoo-l10n_se/l10n_se_account_fiscal_year",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_fiscal_year_vrtl",
        "date_range",
    ],
    "data": [
        "data/date_range_type_data.xml",
    ],
    "pre_init_hook": "_pre_init_adopt_legacy_types",
    "post_init_hook": "_generate_swedish_date_ranges",
    "installable": True,
    "application": False,
    "auto_install": False,
}
