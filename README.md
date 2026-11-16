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

## Demo data

Three modules build a demo company you can load quarter by quarter. The
point is to have something to test reports against: VAT returns, balance
sheets, general ledger, aged lists, bank reconciliation.

Module | Description
--- | ---
l10n_se_demo_company | The company, 619 anonymised customers and suppliers, 9 employees, the journals, the `demo.dataset` model and the wizard. No transactions.
l10n_se_account_demo | Customer and supplier invoices, bank transactions and stock moves, 2023Q4–2027Q4, loaded through the wizard. Also generates the ISO 20022 files (pain.001, camt.053) for 2026Q2–Q4.
l10n_se_payroll_demo (in odoo-l10n_se_payroll) | Payroll runs for the same quarters, posted and paid.

### Loading

Finance → Configuration → Demo data. Pick a source, then load the next
quarter. The quarters are loaded in order — 2023Q4 first, 2027Q4 last —
and removing one takes every higher quarter with it. The wizard shows what
a removal would take before you confirm.

Without the web interface:

```python
env['demo.dataset'].action_load_by_name('2026Q2', 'account')
env['demo.dataset'].action_unreconcile_by_name('2026Q2', 'account')
env['demo.dataset'].action_remove_by_name('2026Q2', 'account')
```

### What is reconciled

2023Q4–2026Q1 is loaded fully reconciled: invoices are paid and the bank
lines are matched. 2026Q2–Q4 carries the ISO 20022 files so the
reconciliation can be done by hand — unreconcile a quarter and import the
statement. 2027 is future data with no files.

### Where the data comes from

Accounting: the SFA production database, anonymised. Customer and supplier
names, organisation numbers, VAT numbers, addresses and bank giro numbers
are all invented; the structure — how many, how they split between
customers and suppliers, how they split between companies and persons — is
preserved. SFA's accounting starts 2023-10-31, which is why the line starts
at 2023Q4.

Payroll: `l10n_se_hr_payroll_tiichri` is the template. It is course
material — seven employees, twelve months, verified against external facit
PDFs — and it is left untouched. 2024 uses its data directly, moved to
2024; 2025–2027 follow the same shape with wages rising each year and the
variations the plan asks for (sickness, parental leave, holiday, bonus,
overtime, wellness grant, salary exchange, part-time).

### Facit

`l10n_se_payroll_demo/data/facit/` holds a frozen result per quarter for
payroll, accounting and the combination. It catches regressions: if a
rule, an account mapping or a tax table changes, the figures move and the
test fails. It does not prove the calculation is correct — that was done
once against the external Tiichri facit in
`fix-l10n-se-payroll-taxtable-lookup`.

2024's facit deviates slightly from the Tiichri PDFs (Asse +3120, Camilla
+7634, Doris −875, Frans +2520 in January). The reason is documented in
`openspec/changes/l10n-se-demo-datasets/design.md`: the dates shift by
whole weeks to keep the weekday, and each employee has their own mix of
part-day and whole-day leaves that the shift moves differently.
