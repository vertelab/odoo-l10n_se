# Plan: l10n_se_payroll_agd — Arbetsgivardeklaration

## Sammanfattning

**Arbetsgivardeklarationen (AGD)** saknas helt som fungerande modul. Spåren i `l10n_se_tax_report` (`# ~ from . import agd`, `agd_journal`, finansiell rapportstruktur) är en påbörjad men aldrig färdigställd implementation. AGD är skild från momsredovisning — data kommer från lönesystemet, inte från bokföringen — och hör därför hemma i payroll-repot, inte i tax_report-repot.

**Mål:** Skapa modulen `l10n_se_payroll_agd` i `/usr/share/odoo-l10n_se_payroll/` som implementerar full AGD: aggregera lönerader per anställd och månad → beräkna SKV-rutor → generera eSKD XML → skicka till Skatteverket via API.

---

## Var den nya modulen ska bo

```
/usr/share/odoo-l10n_se_payroll/l10n_se_payroll_agd/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── agd_declaration.py          # account.agd.declaration (ärver account.declaration)
├── views/
│   └── agd_declaration_views.xml   # Formulär, lista, kalender
├── data/
│   └── agd_cron_data.xml           # Cron för automatisk skapande
├── security/
│   └── ir.model.access.csv
└── demo/
    └── agd_demo.xml                # Demo: 1-2 anställda, 1 lönekörning, 1 AGD
```

---

## Beroenden

```
depends:
  - l10n_se_hr_payroll           # Löneberäkning: hr.payslip + hr.payslip.run
  - l10n_se_tax_report           # account.declaration basklass med SKV API-infrastruktur
  - l10n_se_tax_account          # enable_skatteverket_api, check_valid_access_token
  - payroll                      # OCA: hr.payslip.line, hr.employee etc.
  - hr                           # Anställda
```

---

## Modell: account.agd.declaration

Ärver från `account.declaration` (samma bas som moms och periodisk sammanställning). Får därmed:
- `state` (draft/confirmed/done/canceled) workflow
- `skv_api_status`, `skv_response`, `skv_submitted_date` — SKV API-fält
- `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()` — SKV API-hjälpmetoder
- `create_event()` — kalenderhändelse
- `event_id` — länk till calendar.event

### Egna fält

| Fält | Typ | Beskrivning |
|---|---|---|
| `payslip_run_id` | Many2one → `hr.payslip.run` | Lönekörningen denna AGD baseras på |
| `line_ids` | One2many → `account.agd.declaration.line` | AGD-rader (en per anställd: personnummer + belopp) |
| `agd_file` | Binary | Genererad eSKD XML-fil |
| `agd_file_name` | Char | Filnamn |
| `employee_count` | Integer | Antal anställda med lönerader |
| `total_salary` | Monetary | Total bruttolön |
| `total_employer_fee` | Monetary | Total arbetsgivaravgift |
| `total_tax_withheld` | Monetary | Total avdragen preliminärskatt |
| `total_to_pay` | Monetary | Att betala totalt (avgift + skatt) |
| `currency_id` | Many2one → res.currency | Valuta |

### AGD-linjemodell: account.agd.declaration.line

| Fält | Typ | Beskrivning |
|---|---|---|
| `agd_id` | Many2one → account.agd.declaration | AGD-deklaration |
| `employee_id` | Many2one → hr.employee | Anställd |
| `personal_number` | Char | Personnummer (från employee) |
| `r50_bruttolon` | Monetary | Ruta 50: Avgiftspliktig bruttolön |
| `r51_formaner` | Monetary | Ruta 51: Avgiftspliktiga förmåner |
| `r52_avdrag` | Monetary | Ruta 52: Avdrag för utgifter i arbetet |
| `r55_full_avg_underlag` | Monetary | Ruta 55: Underlag full arbetsgivaravgift (<65 år) |
| `r56_full_avg` | Monetary | Ruta 56: 31,42% av rad 55 |
| `r57_vaxa_underlag` | Monetary | Ruta 57: Underlag växa-stöd |
| `r58_vaxa_avg` | Monetary | Ruta 58: 10,21% av rad 57 |
| `r59_aldersp_underlag` | Monetary | Ruta 59: Underlag 66-79 år |
| `r60_aldersp_avg` | Monetary | Ruta 60: 16,36% av rad 59 |
| `r61_sl_aldre_underlag` | Monetary | Ruta 61: Underlag särskild löneskatt ≥80 år |
| `r62_sl_aldre_avg` | Monetary | Ruta 62: 6,15% av rad 61 |
| `r81_skatteavdrag_underlag` | Monetary | Ruta 81: Underlag för skatteavdrag |
| `r82_avdragen_skatt` | Monetary | Ruta 82: Avdragen preliminärskatt |

---

## Dataflöde

```
hr.payslip.run (månadens lönekörning, state='done')
    │
    ├── slip_ids → hr.payslip (per anställd)
    │       ├── employee_id → personnummer, ålder
    │       └── line_ids → hr.payslip.line
    │               ├── salary_rule_id.code → "gl", "bl", "sa", "total_skatt" etc.
    │               ├── total → belopp
    │               └── category_id → avgiftsplikt / förmån / avdrag
    │
    ▼
account.agd.declaration.calculate()
    │
    ├── Iterera payslip.line_ids per anställd
    ├── Gruppera enligt salary_rule.code → AGD-rutor (50–88)
    ├── Beräkna procentsatser (r56=31,42%, r58=10,21%, r60=16,36%, r62=6,15%)
    ├── Skapa account.agd.declaration.line per anställd
    │
    ▼
generate_agd_file()
    │
    ├── Bygg eSKD XML (samma DTD 6.0 som moms, men AGD-element)
    │
    ▼
action_send_to_skv()
    │
    ├── Hämta partner + access token (ärvt från basen)
    ├── POST till company.skv_agd_api_url
    └── Uppdatera skv_api_status/skv_response
```

### eSKD XML-format

```xml
<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "...">
<eSKDUpload Version="6.0">
  <OrgNr>5561234567</OrgNr>
  <Arbetsgivardeklaration>
    <Period>202604</Period>
    <Anstalld>
      <PersonNr>198001011234</PersonNr>
      <Ruta50>35000</Ruta50>
      <Ruta55>35000</Ruta55>
      <Ruta56>10997</Ruta56>
      <Ruta81>35000</Ruta81>
      <Ruta82>10500</Ruta82>
    </Anstalld>
  </Arbetsgivardeklaration>
</eSKDUpload>
```

---

## Implementation — Steg för steg

### Steg 1: Skapa modulstruktur

Skapa katalogen `l10n_se_payroll_agd/` med alla boilerplate-filer.

### Steg 2: account.agd.declaration modell + line-modell

**Fil:** `models/agd_declaration.py`

Två modeller:
- `account.agd.declaration` — ärver `account.declaration`, lägger till `payslip_run_id`, `line_ids`, `agd_file`, sammanfattningsfält
- `account.agd.declaration.line` — en rad per anställd med samtliga AGD-rutor (50–82)

### Steg 3: calculate() — kärnlogiken

1. Hitta `hr.payslip.run` för perioden (antingen explicit vald eller matcha `date_start`–`date_stop`)
2. Iterera `slip_ids` (lönespecar per anställd)
3. Per lönespec, iterera `line_ids` och matcha `salary_rule_id.code` → AGD-rutor
4. Bestäm ålder för procentsats: <65 → 31,42%, 66–79 → 16,36%, ≥80 → 6,15%
5. Skapa `account.agd.declaration.line` per anställd
6. Sätt `state = 'confirmed'` och generera XML

Nyckelkoder från `hr.payslip.line` (`salary_rule_id.code`):
| Kod | AGD-ruta |
|---|---|
| `bl` / `gl` | Ruta 50, 55, 81 |
| (förmånskoder) | Ruta 51 |
| (avdragskoder) | Ruta 52 |
| `sa` | Ruta 56/58/60/62 (procentsats) |
| `total_skatt` | Ruta 82 |

### Steg 4: generate_agd_file()

Producera eSKD XML med lxml.etree — samma DTD 6.0-referens som momsdeklarationen.

### Steg 5: action_send_to_skv()

Återanvänd ärvda metoder:
1. `self._get_skv_partner()` + `self._get_skv_access_token(partner)`
2. POST XML till `company.skv_agd_api_url`
3. Hantera 200/401/error — uppdatera `skv_api_status`

### Steg 6: Lägg till skv_agd_api_url

I `l10n_se_tax_report/models/res_config.py`:
- `skv_agd_api_url` på `res.company` (computed med test/live default)
- Default test: `https://test.api.skatteverket.se/arbetsgivare/v2/deklaration`
- Default prod: `https://api.skatteverket.se/arbetsgivare/v2/deklaration`

I `l10n_se_tax_report/views/res_config_view.xml`: synligt fält under SKV API.

### Steg 7: Cron

```xml
<record id="ir_cron_agd_declaration" model="ir.cron">
    <field name="name">AGD: create next period</field>
    <field name="model_id" ref="model_account_agd_declaration"/>
    <field name="code">model._cron_create_agd()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
</record>
```

### Steg 8: Views

Formulär med:
- Header: Beräkna, Skicka till Skatteverket, Draft/Done/Cancel, SKV-status badge
- Stat-knappar: Antal anställda, lönesummor, nedladdning, kalender
- Periodväljare, lönekörningsväljare
- Notebook: Inställningar, Anställda (lista), Skatteverket API, Upplysningstext

Listvy med: Namn, datum, antal anställda, totalsummor, status, SKV-status

Kalendervy: deadline i kalendern

### Steg 9: Menypost

```xml
<menuitem id="menu_agd" name="Arbetsgivardeklaration"
    parent="l10n_se_hr_payroll.menu_payroll_reports"
    action="action_agd_declaration"/>
```

### Steg 10: Demo-data

`demo/agd_demo.xml` — `<function>`-tag som kör Python-generator:
1. Skapar anställda med personnummer om de inte finns
2. Skapar lönekörning + lönespecar för innevarande månad
3. Skapar och beräknar en AGD

---

## Filer att skapa / modifiera

| Fil | Status | Ändring |
|---|---|---|
| `l10n_se_payroll_agd/__init__.py` | NY | `from . import models` |
| `l10n_se_payroll_agd/__manifest__.py` | NY | Metadata, dependencies |
| `l10n_se_payroll_agd/models/__init__.py` | NY | `from . import agd_declaration` |
| `l10n_se_payroll_agd/models/agd_declaration.py` | NY | `account.agd.declaration` + line-modell |
| `l10n_se_payroll_agd/views/agd_declaration_views.xml` | NY | Form, list, calendar, search |
| `l10n_se_payroll_agd/data/agd_cron_data.xml` | NY | Cron |
| `l10n_se_payroll_agd/security/ir.model.access.csv` | NY | Access rights |
| `l10n_se_payroll_agd/demo/agd_demo.xml` | NY | Demo-data |
| `l10n_se_tax_report/models/res_config.py` | ÄNDRA | + `skv_agd_api_url` |
| `l10n_se_tax_report/views/res_config_view.xml` | ÄNDRA | + `skv_agd_api_url` |

---

## Återanvändning av befintlig kod

| Befintlig funktion | Plats | Återanvänds för |
|---|---|---|
| `account.declaration` | `l10n_se_tax_report/models/moms.py` | Basmodell: state workflow, SKV API, kalender |
| `_calculate_vat_deadline()` | `l10n_se_tax_report/models/moms.py` | AGD-deadline |
| `_get_skv_settings()` | `l10n_se_tax_report/models/moms.py` | SKV API-inställningar |
| `_get_skv_partner()` | `l10n_se_tax_report/models/moms.py` | SKV API-partner |
| `_get_skv_access_token()` | `l10n_se_tax_report/models/moms.py` | OAuth2 certifikat |
| `create_event()` | `l10n_se_tax_report/models/moms.py` | Kalenderhändelse |
| `skv_*` fält på `res.company` | `l10n_se_tax_report/models/res_config.py` | Test/live-mode, auth |
| `hr.payslip.run` | `l10n_se_hr_payroll/models/hr_payslip_run.py` | Lönedata per månad |
| `hr.payslip` | `l10n_se_hr_payroll/models/hr_payslip.py` | Lönedata per anställd |
| `hr.payslip.line` | `payroll` OCA | Lönerader med salary rule codes |
| `agd_report_*` | `l10n_se_tax_report/data/account_financial.xml` | Referens för ruta 50-82 mappning |
| `eSKDUpload` DTD 6.0 | `l10n_se_tax_report/models/mis_report_generator.py` | XML + DTD-referens |
| `enable_skatteverket_api` | `l10n_se_tax_account/models/partner.py` | Partner-konfiguration |
| `check_valid_access_token()` | `l10n_se_tax_account/models/partner.py` | Token-validering |

---

## Verifiering

1. **Installation:** Modulen installeras utan fel
2. **AGD från lönekörning:** Skapa AGD → `calculate()` aggregerar lönerader per anställd
3. **Åldersprocentsatser:** <65 får 31,42%, 66-79 får 16,36%, ≥80 får 6,15%
4. **eSKD XML:** `generate_agd_file()` producerar giltig XML med rätt DTD
5. **SKV-knapp:** "Skicka till Skatteverket" fungerar
6. **Kalender:** Deadline syns i kalendern
7. **Cron:** AGD skapas automatiskt
8. **Demo:** Installera med demo-data → 1 AGD med ≥1 anställd
9. **Listvy:** Alla AGD:er syns med status och belopp
10. **Nedladdning:** Ladda ner AGD-fil som XML

---

## Risker och öppna frågor

1. **SKV:s AGD XML-elementnamn:** De exakta XML-elementen måste verifieras mot Skatteverkets AGD-DTD. Kan skilja sig från planens antaganden.
2. **Salary rule-koder:** Exakta koder för förmåner och avdrag beror på löneregelkonfigurationen i `l10n_se_hr_payroll`. Kan behöva extra konfiguration.
3. **AGD API-endpoint:** Den faktiska URL:en måste bekräftas mot Skatteverkets API-spec.
4. **Period-matchning:** AGD-månad måste valideras mot lönekörningens period för att undvika mismatch.
