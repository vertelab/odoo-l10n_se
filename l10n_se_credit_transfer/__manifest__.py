# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Swedish Credit Transfer (ISO 20022)",
    "summary": "Generate ISO 20022 XML payment files for Swedish domestic credit transfers (SEK)",
    "description": """
Usage
=====

1. Activate the payment methods under Invoicing > Configuration > Payment Methods.
   Three methods are available:
   - **Swedish Credit Transfer** (pain.001.001.03) — for IBAN/BBAN bank accounts.
   - **Swedish Bankgiro Transfer** (pain.001.001.03) — for Bankgiro bank accounts (7–8 digits).
   - **Swedish Credit Transfer 2.0** (Swedbank MIG 2.0).

2. Create a separate bank journal and payment mode for each account type.
   - **Bankgiro journal**: create a bank account with your Bankgiro number (7–8 digits)
     and connect it to a payment mode using **Swedish Bankgiro Transfer**.
   - **Standard journal**: create a bank account with IBAN and connect it to
     a payment mode using **Swedish Credit Transfer**.

3. Set **SE Initiating Party Identifier** on each payment mode — your bank agreement ID.
   Format: 9–35 alphanumeric characters (A–Z, 0–9).
   For Swedbank MIG 2.0: ``nnnnnnnnnORInnnn``.

4. Optionally set **SE Corporate Pay Agreement ID** for MIG 2.0.
   Format: ``nnnnnnnnnCPOnnnn``.

5. Ensure the company address has a **Town/City** set (mandatory from Nov 2026).

6. Create payment orders from the appropriate journal for each payment type.
   The generator auto-detects the account type and generates valid ISO 20022 XML.

Supported transaction types
---------------------------
- **IBAN** accounts → ``<IBAN>`` element.
- **Bankgiro** (7–8 digit account number) → ``<Othr><Id>`` + ``<SchmeNm><Prtry>BGNR``.
- **PlusGiro / BBAN** → ``<Othr><Id>`` + ``<SchmeNm><Cd>BBAN``.
    """,
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Vertel Sverige AB, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment",
    "category": "Banking",
    "depends": [
        "account_payment_order",
        "account_payment_order_pending",
        "account_banking_pain_base",
    ],
    "data": [
        "data/account_payment_method.xml",
        "views/account_payment_mode.xml",
        "views/account_payment_order.xml",
        "views/account_payment_method.xml",
        "views/account_journal.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "auto_install": False,
}
