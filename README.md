# odoo-l10n_se
Swedish accounting. 4

Testa webhook2
Important! // Viktigt! <br>
Read to install!<br>
https://vertel.se/bokforing/installera-l10n-se

<b>After `sudo update` with a new nightly version of Odoo:</b> <br>
sudo rm -rf /usr/share/core-odoo/addons/l10n_se <br>
sudo rm -rf /usr/share/core-odoo/addons/l10n_se_ocr <br>



Module | Description
--- | --- 
account_change_plan 	|
l10n_se 	|
l10n_se_account_bank_statement_import 	|
l10n_se_account_payment_order 	|
l10n_se_bank | Basemodule for bank-drivers
l10n_se_bgmax |	Bankgirocentralen
l10n_se_budget |	
l10n_se_dibs | reconcile DIBS-transactions
l10n_se_hr_expense | 	
l10n_se_intrastat |	
l10n_se_izettle |	reconcile iZettle-transactions
l10n_se_klarna 	| reconsile Klarna-transactions
l10n_se_nordbanken | (not complete)
l10n_se_paypal 	| reconsile Paypal-transactions
l10n_se_purchase_products |	
l10n_se_seb 	| reconsile SEB-accounts
l10n_se_sie 	| SIE-import/export
l10n_se_skv 	|
l10n_se_swedbank | reconcile Swedbank-accounts
l10n_se_tax_report | Moms- and Agd-report, depends on report_glabels (odoo-report)
l10n_se_yearend_report | SRU-report

## Porteringsstatus — Odoo 19.0

Den här grenen är Odoo 19.0. Tabellen beskriver bara 19.0.

Genererad av `scripts/porting-status.py` — handredigera inte.

| Modul | Funktionsbeskrivning | Porteringsstatus |
|---|---|---|
| `bank_statment_import_id` | Prevent duplicate bank statement imports by adding unique_import_id to CAMT parsers. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_account_bank_statement_import` | Base Module for Import of Swedish Account Bank Statements. | ✓ `18.0.1.1.0` install · 0 p-filer |
| `l10n_se_account_closing` | Swedish K2 closing template for OCA account_fiscal_year_closing | ✓ `18.0.1.0.0` ✗ · 0 p-filer<br>⚠ `account_fiscal_year_closing` (finns inte i något addons-repo) |
| `l10n_se_account_demo` | Swedish demo accounting data — journal entries, invoices, partners from Scalinq AB. | ✓ `18.0.2.8.0` install · 0 p-filer |
| `l10n_se_account_financial_report` | Sweden - Account Financial Report | ✓ `18.0.0.0.0` install · 0 p-filer |
| `l10n_se_account_lms` | Swedish accounting education — system-independent theory with Odoo practice guides. | ✓ `18.0.1.0.6` install · 0 p-filer |
| `l10n_se_account_payment_order` | Swedish Payment Order Configuration. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_account_payment_order_lms` | Svensk utbildning om betalorder, pending-state och bankavstämning via website_slides | ✓ `18.0.1.1.0` install · 0 p-filer |
| `l10n_se_agi` | Swedish AGI (Arbetsgivardeklaration individuppgifter) and KU (Kontrolluppgifter) generation. | ✓ `18.0.1.0.1` install · 0 p-filer |
| `l10n_se_bank` | Adds support for swedish bank account formats. | ✓ `18.0.0.1.0` install · 0 p-filer |
| `l10n_se_bank_statement_counterpart` | Book imported bank statement lines directly against a real counterpart account instead of a suspense/interim account. | ✓ `18.0.1.0.2` install · 0 p-filer |
| `l10n_se_bokslut` | Sweden - Year-End Closing and Annual Report | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_credit_transfer` | Generate ISO 20022 XML payment files for Swedish domestic credit transfers (SEK) | ✓ `18.0.1.1.0` install · 0 p-filer |
| `l10n_se_date_ranges` | Swedish quarter and week date range types for account_fiscal_year_vrtl. | ✓ `18.0.1.2.0` install · 0 p-filer |
| `l10n_se_default_k2` | Satt Vertels K2-kontoplan som standard for svenska foretag. | ✓ `18.0.1.1.0` install · 0 p-filer |
| `l10n_se_default_k3` | Satt BAS K3-kontoplan som standard for svenska foretag. | ✓ `18.0.1.1.0` install · 0 p-filer |
| `l10n_se_demo_company` | Shared demo company for accounting and payroll demo data. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_demo_validation` | Guards Odoo demo data against non-Swedish chart of accounts | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_extended` | Sweden - Chart of accounts. | ✓ `18.0.1.3.0` install · 0 p-filer |
| `l10n_se_fiscal_position` | Adds support for Big Business around the globe!. | ✓ `18.0.0.1.0` install · 0 p-filer |
| `l10n_se_intrastat_product` | Swedish Intrastat Product Declaration (SCB EDAS XML) | ✓ `18.0.1.0.0` ✗ · 0 p-filer<br>⚠ `intrastat_product` (finns inte i något addons-repo) |
| `l10n_se_kommun` | Sweden Kommun - Chart of accounts. | ✓ `18.0.1.4.1` install · 0 p-filer |
| `l10n_se_migration_fortnox` | Migrate accounting data from Fortnox (plus Visma/Bokio via SIE) to Odoo. | ✓ `18.0.1.3.0` install · 0 p-filer |
| `l10n_se_mis` | Create Swedish MIS-reports. | ✓ `18.0.2.0.9` install · 0 p-filer |
| `l10n_se_mis_k2` | Swedish MIS-reports for Aktiebolag enligt K2 (BFNAR 2016:10). | ✓ `18.0.2.0.1` install · 0 p-filer |
| `l10n_se_mis_k2_filial` | Swedish MIS-reports for Filial till utländskt företag enligt K2 (BFNAR 2016:10) | ✓ `18.0.2.0.0` install · 0 p-filer |
| `l10n_se_mis_k2_forening` | Swedish MIS-reports for Ekonomisk förening enligt K2 (BFNAR 2016:10) | ✓ `18.0.2.0.0` install · 0 p-filer |
| `l10n_se_mis_k2_handelsbolag` | Swedish MIS-reports for Handels- och kommanditbolag enligt K2 (BFNAR 2016:10). | ✓ `18.0.2.0.0` install · 0 p-filer |
| `l10n_se_mis_k3` | Swedish MIS-reports for Aktiebolag enligt K3 (BFNAR 2012:1). | ✓ `18.0.2.0.1` install · 0 p-filer |
| `l10n_se_mis_k3_koncern` | Swedish MIS-reports for koncernredovisning enligt K3 (BFNAR 2012:1). | ✓ `18.0.2.0.0` install · 0 p-filer |
| `l10n_se_mis_kommun` | Svenska Kommun MIS-reports. | ✓ `18.0.2.0.0` install · 0 p-filer |
| `l10n_se_municipality_class` | A list of Swedish Municipalities. | ✓ `18.0.0.1.0` install · 0 p-filer |
| `l10n_se_mynt` | Handles Mynt Transactions. | ✓ `18.0.1.0.1` install · 0 p-filer |
| `l10n_se_ocr` | Adds Swedish OCR number support with configurable control levels. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_ocr_reconcile` | Bridge module to match Swedish OCR numbers from bank feeds with invoices via OCA reconciliation. | ✓ `18.0.1.0.2` install · 0 p-filer |
| `l10n_se_payroll_lms` | Swedish payroll education — system-independent theory with Odoo practice guides. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_sie` | Module for importing SIE-files. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_sie_minimal` | Module for importing SIE-files. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_skatteverket_api` | Sweden - Shared Skatteverket API module. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_tax_account` | Sweden - Tax Account Reconciliation (Skattekontoavstämning) | ✓ `18.0.2.0.0` ✗ · 0 p-filer<br>⚠ `account_statement_reconcile_status` (odooext-OCA-account-reconcile; 19.0-grenen är tom) |
| `l10n_se_tax_display_name` | Show tax description instead of name in selection fields and dropdowns. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `l10n_se_tax_report` | Sweden - Account Tax Report | ✓ `18.0.1.5.6` install · 0 p-filer |
| `l10n_se_tax_report_payment_order` | Payment order support for tax declarations. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `mis_builder_annotation_init_fix` | Guard mis.report.instance.annotation.init() against missing table | ✓ `1.0.0` install · 0 p-filer |
| `mis_builder_fixes` | Collection of fixes for mis_builder bugs. | ✓ `18.0.1.0.0` install · 0 p-filer |
| `mis_cash_flow` | MIS Cash flow template. | ✓ `18.0.1.1.0` install · 0 p-filer |
| `mis_export_import` | Export and Import MIS Report templates with all related data (KPIs, Styles, Queries, etc.). | ✓ `18.0.0.0.0` install · 0 p-filer |
