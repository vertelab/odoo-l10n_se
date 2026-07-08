{
    "name": "Swedish Account Closing Bridge",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Swedish K2/K3 closing templates for OCA account_fiscal_year_closing",
    "description": """
Bridge module providing Swedish K2/K3 closing templates for the OCA
account_fiscal_year_closing module.

Features:
- K2 closing template with Swedish account mappings
- K3 closing template with Swedish account mappings
- Integration with l10n_se_bokslut for tax calculation
    """,
    "author": "Vertel AB",
    "website": "https://www.vertel.se",
    "license": "AGPL-3",
    "depends": [
        "account_fiscal_year_mis",
        "account_fiscal_year_closing",
        "l10n_se",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/closing_template_k2.xml",
        "data/closing_template_k3.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
