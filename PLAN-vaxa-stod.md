# Plan: `l10n_se_payroll_growth_support` — Växa-stöd

## Context

Skatteverket erbjuder **Växa-stöd** — en återbetalning av arbetsgivaravgifter för företag som anställer sin första (och andra) medarbetare. Från och med **januari 2026** är systemet ändrat: istället för nedsatta avgifter via ruta 57/58 i AGD, betalar arbetsgivaren **full arbetsgivaravgift (31,42%)** och **ansöker separat om återbetalning** av mellanskillnaden (31,42% − 10,21% = 21,21%).

### Regler i korthet
| Parameter | Anställd före 1 maj 2024 | Anställd efter 30 april 2024 |
|---|---|---|
| Lönetak för stöd | 25 000 kr/mån | 35 000 kr/mån |
| Återbetalning per månad | 25 000 × 21,21% = 5 302 kr | 35 000 × 21,21% = 7 423 kr |
| Max antal anställda | 2 (första + andra) | 2 (första + andra) |
| Max månader | 24 kalendermånader i följd | 24 kalendermånader i följd |
| De minimis-tak | 300 000 € på 3 år | 300 000 € på 3 år |

Företaget måste kvalificera som **växa-företag** (max 1 anställd sedan 1 jan 2024, delägare/närstående räknas ej). Anställningen måste vara minst 3 månader, minst 20 tim/vecka.

### API-läge
Skatteverket har API:er för moms (Momsdeklaration) och AGD (Arbetsgivardeklaration), men per juni 2026 verkar Växa-stöd-ansökan **endast gå via e-tjänst (webbformulär)**. Modulen ska förberedas för API-inlämning när/om det kommer, med samma autentiseringsmönster som `l10n_se_tax_report`.

---

## Approach

Skapa en ny Odoo-modul `l10n_se_payroll_growth_support` som:

1. **Ärver `account.declaration`** — återanvänder all SKV API-infrastruktur (token, cert, endpoints, status, response), calendar integration och state machine från `l10n_se_tax_report`.
2. **Knyts till lönekörningar** (`hr.payslip.run`) och/eller AGD-deklarationer (`account.agd.declaration`) för att hämta löneunderlag.
3. **Beräknar återbetalningsbelopp** per anställd baserat på anställningsdatum, månadslön och lönetak.
4. **Hanterar ansökningsprocessen** — spårar status (utkast → beräknad → inskickad → beviljad/avslagen), deadline, återbetalning på skattekonto.
5. **Stödjer både manuell hantering** (ladda ner PDF/sammanställning för e-tjänst) och **framtida API-inlämning** (samma mönster som `action_send_to_skv()`).

---

## Files to create

```
l10n_se_payroll_growth_support/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── vaxa_support.py          # account.vaxa.support + account.vaxa.support.line
│   └── res_company.py           # Extend res.company with växa-stöd settings
├── views/
│   └── vaxa_support_views.xml   # Form, list, search, calendar views
├── security/
│   └── ir.model.access.csv
├── data/
│   └── vaxa_cron_data.xml       # Cron for auto-creation
└── demo/
    └── vaxa_demo.xml            # Demo data generator
```

---

## Reuse

| What | From | How |
|---|---|---|
| `account.declaration` base class | `l10n_se_tax_report/models/moms.py` | Inherit — gives `date`, `state`, `company_id`, `move_id`, `event_id`, `skv_api_status`, `skv_response`, `skv_submitted_date`, `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()`, `create_event()`, `_calculate_vat_deadline()` |
| `res.company` SKV fields | `l10n_se_tax_report/models/res_config.py` | `skv_test_mode`, `skv_auth_method`, `skv_api_url`, `skv_token_url`, `skv_auth_url` — already on company; add `skv_vaxa_api_url` |
| `res.partner` SKV API fields | `l10n_se_tax_account/models/partner.py` | `enable_skatteverket_api`, `certificate`, `access_token`, `oauth_client_id` — already on partner |
| `hr.payslip.run` + `hr.payslip` | OCA `payroll` + `l10n_se_payroll_agd` | Link payslip runs to växa-stöd applications |
| AGD calculation pattern | `l10n_se_payroll_agd/models/agd_declaration.py` | `calculate()` — aggregate payslip lines per employee; `_get_employee_age()` |
| AGD views pattern | `l10n_se_payroll_agd/views/agd_declaration_views.xml` | Form with header buttons, statusbar, summary group, employee lines list, SKV API page |
| AGD cron pattern | `l10n_se_payroll_agd/data/agd_cron_data.xml` | `_cron_create_vaxa()` |
| AGD security | `l10n_se_payroll_agd/security/ir.model.access.csv` | Same group structure |
| `workalendar` Swedish calendar | `l10n_se_tax_report` dependency | `_calculate_vat_deadline()` |

---

## Steps

### Step 1: Create module skeleton
- [ ] Create directory structure under `/usr/share/odoo-l10n_se_payroll/l10n_se_payroll_growth_support/`
- [ ] `__manifest__.py` — depends on `l10n_se_hr_payroll`, `l10n_se_tax_report`, `l10n_se_payroll_agd`, `payroll`, `hr`; Python deps `lxml`, `requests`
- [ ] `__init__.py` and `models/__init__.py`

### Step 2: Extend `res.company` for Växa-stöd settings
- [ ] `models/res_company.py` — inherit `res.company`:
  - `skv_vaxa_api_url` (Char, computed from test mode, default pattern like other SKV URLs)
  - `vaxa_support_enabled` (Boolean)
- [ ] Also extend `res.config.settings` for the settings UI

### Step 3: Core model `account.vaxa.support`
- [ ] `models/vaxa_support.py` — `account.vaxa.support` inheriting `account.declaration`:
  - `_report_name = 'Växa-stöd'`
  - `payslip_run_id` (Many2one → `hr.payslip.run`)
  - `agd_declaration_id` (Many2one → `account.agd.declaration`, optional link to AGD)
  - `line_ids` (One2many → `account.vaxa.support.line`)
  - Summary fields: `employee_count`, `total_salary`, `total_reimbursement`, `total_de_minimis`
  - `currency_id` (related to company)
  - `date_start`, `date_stop` (period, auto-filled from payslip run)
  - `application_deadline` (Date, 1 year after period end)

### Step 4: Line model `account.vaxa.support.line`
- [ ] In same `vaxa_support.py`:
  - `vaxa_id` (Many2one → `account.vaxa.support`)
  - `employee_id` (Many2one → `hr.employee`)
  - `personal_number` (Char)
  - `contract_id` (Many2one → `hr.contract`, for hire date)
  - `hire_date` (Date, from contract)
  - `monthly_salary` (Monetary)
  - `salary_cap` (Monetary, computed: 25000 or 35000 based on hire_date)
  - `basis_for_support` (Monetary, min of salary and cap)
  - `reimbursement_amount` (Monetary, basis × 21.21%)
  - `months_used` (Integer, how many of 24 months already claimed)
  - `months_remaining` (Integer, computed)
  - `employee_number` (Selection: first/second)
  - `de_minimis_used` (Monetary, running total)

### Step 5: Calculation method `calculate()`
- [ ] Find payslips from linked `payslip_run_id` (or by date range)
- [ ] Group by employee
- [ ] For each employee, determine:
  - Hire date from contract
  - Salary cap (25000/35000 based on hire date vs May 1, 2024)
  - Monthly gross salary from payslip lines
  - Basis = min(salary, cap)
  - Reimbursement = round(basis × 0.2121)
  - Employee number (first/second based on hire order)
  - Months used so far (count previous vaxa support lines for this employee)
- [ ] Set `state = 'confirmed'`

### Step 6: Views
- [ ] Form view (pattern from AGD form):
  - Header: Beräkna, Skicka till Skatteverket, Draft, Done, Cancel buttons
  - Statusbar with SKV API status badge
  - Sheet: company, payslip run, AGD reference, period dates, deadline
  - Summary group: total salary, total reimbursement, employee count
  - Notebook: Inställningar, Anställda (list), Detaljer, SKV API
- [ ] List view (tree)
- [ ] Search view with filters
- [ ] Calendar view
- [ ] Action + menu item under authorities menu

### Step 7: SKV API submission
- [ ] `action_send_to_skv()` — reuse `_get_skv_partner()` + `_get_skv_access_token()` from base class
- [ ] Build JSON payload with employee data (matching SKV e-service fields)
- [ ] POST to `skv_vaxa_api_url` (or generate downloadable summary if no API)
- [ ] Handle response, update `skv_api_status`, `skv_response`, `skv_submitted_date`
- [ ] Generate downloadable summary (PDF or structured data) for manual e-service fallback

### Step 8: Security + cron
- [ ] `security/ir.model.access.csv` — same groups as AGD
- [ ] `data/vaxa_cron_data.xml` — cron job calling `_cron_create_vaxa()`
- [ ] `_cron_create_vaxa()` — find latest AGD/payslip run without växa application, create + calculate

### Step 9: Demo data
- [ ] `demo/vaxa_demo.xml` — demo generator (like `AgdDemoGenerator`):
  - Create demo employee with contract and payslip
  - Create växa-stöd application
  - Calculate and show results

### Step 10: Integration touchpoints
- [ ] Add `vaxa_support_id` field on `hr.payslip` (or `hr.payslip.run`) for traceability
- [ ] Add reference from `account.agd.declaration` to `account.vaxa.support`

---

## Verification

1. **Install module** on `scalinq-moms` database:
   ```bash
   odoo -d scalinq-moms -i l10n_se_payroll_growth_support --stop-after-init
   ```
2. **Check UI**: Växa-stöd menu appears under Authorities, form loads
3. **Create demo data**: Run demo generator, verify employees and amounts
4. **Manual test**: Create a payslip run → create AGD → create Växa-stöd application → verify calculation
5. **SKV connection**: Test with Skatteverket test environment (if API endpoint exists) or verify downloadable summary
6. **Run tests**: Any existing test infrastructure
