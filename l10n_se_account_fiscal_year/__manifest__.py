{
    "name": "Swedish Account Fiscal Year Bridge",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Swedish date range types and generation for account_fiscal_year_vrtl",
    "description": """
Bridge module connecting account_fiscal_year_vrtl with Swedish date range types.

Features:
- Swedish date range types (fiscalyear, quarter, month, week) with Swedish naming
- Auto-generation of Swedish date ranges on install
- Swedish-specific cron/server action configuration
    """,
    "author": "Vertel AB",
    "website": "https://www.vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account_fiscal_year_vrtl",
        "l10n_se_date_ranges",
    ],
    "data": [
        "data/date_range_type_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "_generate_swedish_date_ranges",
}
