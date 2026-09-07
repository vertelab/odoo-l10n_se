# -*- coding: utf-8 -*-
# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sweden - Intrastat Product Declaration",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "license": "AGPL-3",
    "summary": "Swedish Intrastat Product Declaration (SCB EDAS XML)",
    "author": "Vertel Sverige AB, Odoo Community Association (OCA)",
    "maintainers": [],
    "website": "https://vertel.se/apps/odoo-l10n_se/l10n_se_intrastat_product",
    "depends": [
        "intrastat_product",
        "l10n_se_tax_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/intrastat_transaction.xml",
        "data/intrastat_transport_mode.xml",
        "data/intrastat_region.xml",
        "views/res_config_settings.xml",
        "views/intrastat_product_declaration.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
