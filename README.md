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

## Porteringsstatus

18.0 är baseline. 19.0/20.0 visar om p-filen har ett villkor för utgåvan
— inte om grenen finns. Blockerare är `depends` som saknas i 20.0
(kärna + alla 20.0-grenar).

| Modul | Beskrivning | Manifest | p-fil | 19.0 | 20.0 | Blockerare |
|---|---|---|---|---|---|---|
| bank_statment_import_id | Prevent duplicate bank statement imports by adding unique... | 1.0.0 | 0 | — | — | `account_statement_import_camt` |
| l10n_se_account_bank_statement_import | Base Module for Import of Swedish Account Bank Statements. | 1.0.1 | 0 | — | — | `account_statement_import_file` |
| l10n_se_account_demo | Swedish demo accounting data — journal entries, invoices,... | 2.8.0 | 0 | — | — | — |
| l10n_se_account_financial_report | Sweden - Account Financial Report. | 0.0.0 | 1 | — | ✓ | — |
| l10n_se_account_lms | Swedish accounting education — system-independent theory ... | 1.0.3 | 1 | — | ✓ | — |
| l10n_se_account_payment_order | Swedish Payment Order Configuration. | 1.0.0 | 0 | — | — | `account_payment_order` |
| l10n_se_account_payment_order_lms | Svensk utbildning om betalorder, pending-state och bankav... | 1.1.0 | 1 | — | ✓ | — |
| l10n_se_agi | Swedish AGI (Arbetsgivardeklaration individuppgifter) and... | 1.0.1 | 1 | — | ✓ | — |
| l10n_se_bank | Adds support for swedish bank account formats. | 0.1.0 | 0 | — | — | — |
| l10n_se_bokslut | Sweden - Year-End Closing and Annual Report. | 0.0.1 | 1 | — | ✓ | — |
| l10n_se_credit_transfer | Generate ISO 20022 XML payment files for Swedish domestic... | 1.0.0 | 0 | — | — | `account_payment_order` `account_banking_pain_base` |
| l10n_se_date_ranges | Provides fiscal year, quarter, and month date range types... | 1.1.0 | 0 | — | — | — |
| l10n_se_extended | Sweden - Chart of accounts. | 1.0.1 | 1 | — | ✓ | — |
| l10n_se_fiscal_position | Adds support for Big Business around the globe!. | 0.1.0 | 1 | — | ✓ | — |
| l10n_se_intrastat_product | Swedish Intrastat Product Declaration (SCB EDAS XML) | 1.0.0 | 1 | — | ✓ | `intrastat_product` |
| l10n_se_kommun | Sweden Kommun - Chart of accounts. | 1.0.0 | 0 | — | — | — |
| l10n_se_migration | Migrate accounting data from Fortnox, Visma, Bokio to Odoo. | 1.0.4 | 1 | — | ✓ | — |
| l10n_se_mis | Create Swedish MIS-reports. | 1.9.0 | 1 | — | — | — |
| l10n_se_mis_k2 | Swedish MIS-reports for Aktiebolag enligt K2 (BFNAR 2016:... | 1.4.0 | 1 | — | — | — |
| l10n_se_mis_k2_filial | Swedish MIS-reports for Filial till utländskt företag enl... | 1.0.0 | 1 | — | — | — |
| l10n_se_mis_k2_forening | Swedish MIS-reports for Ekonomisk förening enligt K2 (BFN... | 1.0.0 | 1 | — | — | — |
| l10n_se_mis_k2_handelsbolag | Swedish MIS-reports for Handels- och kommanditbolag enlig... | 1.0.0 | 1 | — | — | — |
| l10n_se_mis_k3 | Swedish MIS-reports for Aktiebolag enligt K3 (BFNAR 2012:1). | 1.0.0 | 1 | — | — | — |
| l10n_se_mis_k3_koncern | Swedish MIS-reports for koncernredovisning enligt K3 (BFN... | 1.0.0 | 1 | — | — | — |
| l10n_se_mis_kommun | Svenska Kommun MIS-reports. | 1.0.0 | 0 | — | — | — |
| l10n_se_municipality_class | A list of Swedish Municipalities. | 0.1.0 | 1 | — | ✓ | — |
| l10n_se_mynt | Handles Mynt Transactions. | 1.0.0 | 1 | — | ✓ | `account_statement_import_file` |
| l10n_se_ocr | Adds Swedish OCR number support with configurable control... | 1.0.0 | 1 | ✓ | — | — |
| l10n_se_ocr_reconcile | Bridge module to match Swedish OCR numbers from bank feed... | 1.0.2 | 0 | — | — | `account_reconcile_oca` |
| l10n_se_payroll_lms | Swedish payroll education — system-independent theory wit... | 1.0.0 | 0 | — | — | — |
| l10n_se_sie | Module for importing SIE-files. | 1.0.0 | 2 | — | ✓ | — |
| l10n_se_sie_minimal | Module for importing SIE-files. | 1.0.0 | 2 | — | ✓ | — |
| l10n_se_skatteverket_api | Sweden - Shared Skatteverket API module. | 1.0.0 | 1 | — | ✓ | — |
| l10n_se_tax_account | Sweden - Tax Account Reconciliation (Skattekontoavstämning) | 2.0.0 | 2 | — | ✓ | `account_reconcile_oca` `account_statement_reconcile_status` |
| l10n_se_tax_display_name | Show tax description instead of name in selection fields ... | 1.0.0 | 0 | — | — | — |
| l10n_se_tax_report | Sweden - Account Tax Report. | 0.0.0 | 2 | — | ✓ | — |
| l10n_se_tax_report_payment_order | Payment order support for tax declarations. | 1.0.0 | 0 | — | — | `account_payment_order` |
| mis_builder_fixes | Collection of fixes for mis_builder bugs. | 1.0.0 | 0 | — | — | — |
| mis_cash_flow | MIS Cash flow template. | 1.1.0 | 0 | — | — | `mis_builder_cash_flow` |
| mis_export_import | Export and Import MIS Report templates with all related d... | 0.0.0 | 1 | — | ✓ | — |
