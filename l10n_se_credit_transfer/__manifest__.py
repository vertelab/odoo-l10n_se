# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Swedish Credit Transfer (ISO 20022)",
    "summary": "Generate ISO 20022 XML payment files for Swedish domestic credit transfers (SEK)",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Vertel AB, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment",
    "category": "Banking",
    "depends": [
        "account_payment_order",
        "account_banking_pain_base",
    ],
    "data": [
        "data/account_payment_method.xml",
        "views/account_payment_mode.xml",
        "views/account_payment_order.xml",
        "views/account_payment_method.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "post_init_hook": "set_default_se_initiating_party",
    "installable": True,
    "auto_install": False,
}
