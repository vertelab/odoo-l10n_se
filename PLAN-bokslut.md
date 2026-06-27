# Plan: l10n_se_bokslut — Bokslut och Årsredovisning

## Sammanfattning

Odoo har redan moms, AGD, SRU och skattekonto — men saknar ett **sammanhållet bokslutsflöde**. Fortnox och Visma har dedikerade bokslutsmoduler som täcker periodiseringsfonder, överavskrivningar, skatteberäkning, bokslutsdokumentation och årsredovisningsgenerering i ett enda arbetsflöde.

**Mål:** Bygga `l10n_se_bokslut` — en ny modul i `odoo-l10n_se` som implementerar bokslutsplanering, bokslutsjusteringar (periodiseringsfonder, överavskrivningar), skatteberäkning, bokslutschecklista, bokslutsdokumentation och årsredovisningsgenerering. Bygger vidare på befintlig `account.sru.declaration` och `account.declaration`-infrastruktur.

---

## Scope — 4 faser

| Fas | Innehåll | Prio |
|-----|----------|------|
| **Fas 1** | Bokslutsplanering + Skatteberäkning + Bokslutsverifikationer | 🔴 Kärnan |
| **Fas 2** | Bokslutschecklista + Bokslutsdokumentation (via project.task + attachments) | 🟠 Högt |
| **Fas 3** | Årsredovisningsgenerering (BR, RR, noter, förvaltningsberättelse) | 🟠 Högt |
| **Fas 4** | Periodiseringsfonder + Överavskrivningar (djup integration) | 🟡 Medium |

---

## Designfilosofi: Återanvänd Odoos project-modul

Istället för att bygga egna checklist- och dokumentationsmodeller från grunden, **återanvänder vi Odoos inbyggda `project`-modul** för visualisering och arbetsflöde. Detta ger oss gratis:

| Odoo pattern | Används för | Ger oss |
|--------------|-------------|---------|
| `project.task` + `stage_id` (kanban) | Bokslutschecklista | Dra-och-släpp mellan stadier, assignering, deadlines, tracking |
| `project.milestone` | Viktiga hållpunkter | Deadline-visualisering, reached/not reached, Gantt |
| `mail.activity` | Påminnelser, deadlines | Schemalagda aktiviteter, notifikationer, chattering |
| `ir.attachment` (chatter) | Bokslutsdokumentation | Bilagor på tasks/journal entries, versionshantering |
| `project.project` | Varje bokslut | Container för tasks, milestones, activities, progress % |

Detta följer Odoos "don't reinvent the wheel"-filosofi och ger användarna en **välbekant UI-upplevelse** (samma som projektmodulen de redan använder).

### Visualisering i praktiken

**Checklistan visas som en Kanban-tavla** (samma som project.task):
- Kolumner: *Att göra* → *Pågående* → *Granskning* → *Klar* → *Ej tillämplig*
- Varje checklistpunkt är en `project.task` med:
  - Beskrivning (HTML, guideline-text)
  - Assignee (vem är ansvarig)
  - Deadline
  - Tags (sektion: Tillgångar, Skulder, Resultat, etc.)
  - Priority (stjärnmärkning för kritiska punkter)
  - Bilagor i chattering (underlag, avstämningar, specifikationer)

**Milestones** markerar viktiga bokslutshållpunkter:
- "Bankavstämning klar"
- "Momsdeklaration inlämnad"
- "SRU genererad"
- "Årsredovisning signerad"
- "Inskickat till Bolagsverket"

**Dokumentation** hanteras via chattering + attachments:
- Varje `project.task` (checklistpunkt) kan ha bilagor (specifikationer, avstämningar, intyg)
- Varje `account.move` (bokslutsverifikation) kan ha bilagor (underlag)
- Intern/extern synlighet via access rights

---

## Var den nya modulen ska bo

```
/usr/share/odoo-l10n_se/l10n_se_bokslut/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── bokslut_planning.py            # account.bokslut — bokslutsplanering (core)
│   ├── bokslut_adjustment.py          # account.bokslut.adjustment — bokslutsjusteringar
│   ├── annual_report.py               # account.annual.report — årsredovisning
│   ├── project_task.py                # project.task — extend with bokslut fields
│   └── res_config.py                  # Inställningar
├── views/
│   ├── bokslut_planning_views.xml
│   ├── bokslut_adjustment_views.xml
│   ├── annual_report_views.xml
│   ├── project_task_views.xml         # Extend project.task kanban/form för bokslut
│   ├── project_project_views.xml      # Extend project.project form för bokslut
│   └── res_config_view.xml
├── data/
│   ├── bokslut_task_stages.xml        # project.task.type: Att göra, Pågående, Klar, etc.
│   ├── bokslut_task_data.xml          # Standard-checklistpunkter som project.task templates
│   ├── annual_report_templates.xml    # Rapportmallar (account.financial.report)
│   └── cron_data.xml                  # Påminnelser, automatisk generering
├── report/
│   └── annual_report_pdf.xml          # QWeb-rapport för årsredovisning
├── security/
│   └── ir.model.access.csv
└── demo/
    └── bokslut_demo.xml
```

---

## Beroenden

```python
depends:
  - l10n_se_tax_report           # account.declaration, account.sru.declaration, SKV API
  - l10n_se_mis                  # MIS-rapportinfrastruktur
  - l10n_se_account_financial_report  # account.financial.report (BR/RR-struktur)
  - l10n_se_extended             # BAS-kontoplan
  - project                      # project.task (kanban-checklista), project.milestone, mail.activity
  - account                      # account.move, account.move.line, account.journal
  - account_period_vrtl          # account.period med svensk räkenskapsperiod
```

---

## Fas 1: Bokslutsplanering + Skatteberäkning

### Modell: `account.bokslut` (ärver `account.declaration`)

**Koncept:** En bokslutsdeklaration är en _container_ för hela bokslutsarbetet. Den knyts till ett räkenskapsår (account.fiscalyear) och har en **kopplad `project.project`** för att visualisera checklistan som en Kanban-tavla med stages, milestones och assignments.

**Arv från `account.declaration`:**
- `state`: draft → confirmed → done → cancel
- `skv_api_status`, `skv_response` — för ev. framtida API-inlämning till Bolagsverket
- `create_event()`, `event_id`
- `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()`

**Egna fält:**

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `fiscalyear_id` | Many2one → account.fiscalyear | Räkenskapsår |
| `period_start` | Many2one → account.period | Startperiod (default: första perioden i året) |
| `period_stop` | Many2one → account.period | Slutperiod (default: sista perioden i året) |
| `project_id` | Many2one → project.project | **Kopplat projekt** — innehåller checklista (tasks) + milstolpar (milestones) |
| `report_id` | Many2one → account.financial.report | Finansiell rapportstruktur (BR/RR) |
| `adjustment_ids` | One2many → account.bokslut.adjustment | Bokslutsjusteringar |
| `tax_calculation_ids` | One2many → account.bokslut.tax.calc | Skatteberäkningsrader |
| `verification_ids` | One2many → account.move | Bokslutsverifikationer (via move_id) |
| `resultat_fore_bokslut` | Monetary | Resultat före bokslutsdispositioner |
| `resultat_fore_skatt` | Monetary | Resultat före skatt |
| `arets_skattekostnad` | Monetary | Beräknad bolagsskatt (20.6%) |
| `arets_resultat` | Monetary | Årets resultat efter skatt |
| `annual_report_id` | Many2one → account.annual.report | Genererad årsredovisning |

**Metoder:**

| Metod | Beskrivning |
|-------|-------------|
| `action_open()` | Öppnar bokslutets planeringsvy |
| `action_create_checklist_project()` | Skapar project.project + kopierar standard-checklista → project.task + milestones |
| `action_open_checklist()` | Öppnar projektets Kanban-vy med bokslutets checklistpunkter |
| `calculate_resultat()` | Beräknar resultat från kontoplanen (konto 3000-8999) |
| `calculate_skatt()` | Skatteberäkning: resultat + justeringar → skattepliktigt resultat → skatt |
| `generate_adjustments()` | Auto-föreslår bokslutsjusteringar |
| `generate_verifications()` | Skapar/uppdaterar bokslutsverifikationer |
| `action_book()` | Slutligt bokför alla verifikationer |
| `action_book_preliminary()` | Preliminärt bokför alla verifikationer |
| `action_generate_annual_report()` | Genererar årsredovisning |
| `action_send_bolagsverket()` | Skickar till Bolagsverket (framtida API) |

### Modell: `account.bokslut.adjustment`

Bokslutsjusteringar som påverkar det skattepliktiga resultatet men som inte nödvändigtvis bokförs (ex: ej avdragsgilla kostnader, ej skattepliktiga intäkter).

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Bokslut |
| `name` | Char | Beskrivning |
| `account_id` | Many2one → account.account | Konto |
| `amount` | Monetary | Belopp |
| `type` | Selection | 'income' (skattepliktig intäkt), 'cost' (avdragsgill kostnad), 'non_deductible' (ej avdragsgill), 'non_taxable' (ej skattepliktig) |
| `is_permanent` | Boolean | Permanent skillnad (påverkar endast skatten) |
| `move_id` | Many2one → account.move | Bokslutsverifikation |

### Modell: `account.bokslut.tax.calc`

Rader i skatteberäkningen:

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Bokslut |
| `sequence` | Integer | Ordning |
| `name` | Char | Beskrivning (t.ex. "Resultat före bokslutsdispositioner") |
| `amount` | Monetary | Belopp |
| `calculation` | Char | Formel (python-eval, t.ex. "sum([adj.amount for adj in bokslut.adjustment_ids if adj.type == 'cost'])") |

### Skatteberäkningslogik

```
Resultat före bokslutsdispositioner  (från kontoplan 3000-8999)
+ Ej avdragsgilla kostnader
- Ej skattepliktiga intäkter
- Schablonintäkt periodiseringsfond  (statlig ränta × summa periodiseringsfonder)
- Återföring av periodiseringsfond
+ Avsättning till periodiseringsfond
- Överavskrivningar
= Skattepliktigt resultat
× 20.6% = Årets skattekostnad
Årets resultat = Resultat före dispositioner - skatt
```

### Views: Bokslutsplanering

Inspirerad av Fortnox "Bokslutsplanering / Skatteberäkning":

**Header:** Räkenskapsår, status, datum, knappar (Beräkna, Bokför, Preliminärbokför)

**Tab 1: Resultat** — Visar kontosaldon 3000-8799 med drill-down. Två kolumner: konto, saldo.

**Tab 2: Bokslutsjusteringar** — Tabell med bokslutsjusteringar. Lägg till/ta bort rader. Summering av justeringarna. Icke skattepliktiga intäkter och ej avdragsgilla kostnader i separata rutor.

**Tab 3: Skatteberäkning** — Visar hela skatteberäkningskedjan steg för steg. Resultatet uppdateras i realtid när justeringar ändras.

**Tab 4: Bokslutsverifikationer** — Samlade verifikationer med status (Förslag/Preliminär/Bokförd). Knappar per verifikation: Visa, Bokför, Preliminärbokför, Ångra.

**Chart of accounts drill-down:** Klicka på kontosummor för att se underliggande verifikationer.

---

## Fas 2: Bokslutschecklista + Dokumentation (via project-modulen)

### Koncept: Bokslut som Project

Varje `account.bokslut` får ett kopplat `project.project`. När bokslutet skapas (eller vid `action_create_checklist_project()`):

1. **Skapa project.project** med namn = "Bokslut <räkenskapsår> — <företag>"
2. **Kopiera standard-checklistpunkter** från templates (`bokslut_task_data.xml`) → `project.task`
3. **Skapa milestones** för viktiga hållpunkter
4. **Lägg till `mail.activity`** för deadlines (t.ex. "Bokslut ska vara klart X dagar före deadline")

Detta ger användaren en full Kanban-tavla där checklistpunkter kan dras mellan stadier, assignas, och kommenteras via chattering.

### Modell: `project.task` — extend

Extenda `project.task` med bokslutsspecifika fält (`models/project_task.py`, `_inherit = 'project.task'`):

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Kopplat bokslut |
| `section` | Selection | Sektion: Tillgångar, Skulder, Resultat, Skatter, Övrigt |
| `account_ids` | Many2many → account.account | Berörda konton (för att länka till kontoplan) |
| `is_required` | Boolean | Obligatorisk checklistpunkt |

**Stages** (`project.task.type`, datafil: `bokslut_task_stages.xml`):
- `Att göra` (default, fold=False)
- `Pågående` (fold=False)
- `Granskning` (fold=False)
- `Klar` (fold=True)
- `Ej tillämplig` (fold=True)

### Standard-checklistpunkter (`data/bokslut_task_data.xml`)

~50 templates baserade på Vismas bokslutschecklista, grupperade i sektioner:

**Tillgångar** (section: 'assets')
- Anläggningstillgångar: kontrollera inköp/försäljning/utrangering mot verifikationer
- Anläggningstillgångar: dokumentera avskrivningsprinciper
- Kassa: stäm av mot bokföring
- Bank/Check/Plusgiro: stäm av mot kontoutdrag
- Kundfordringar: stäm av huvudbok mot reskontra
- Kundfordringar: bedöm osäkra fordringar
- Varulager: inventera och upprätta intyg
- Övriga fordringar: periodisera upplupna intäkter

**Skulder och eget kapital** (section: 'liabilities')
- Leverantörsskulder: stäm av huvudbok mot reskontra
- Skatteskulder: kontrollera beräkning av årets skattekostnad
- Momsredovisning: stäm av årets moms
- Personalskatt: stäm av källskatter
- Semesterlöneskuld: kontrollera
- Arbetsgivaravgifter: stäm av
- Upplupna kostnader: beakta räntor, bonus, retroaktiva löner
- Förutbetalda intäkter: kontrollera

**Resultat** (section: 'result')
- Kontrollera resultaträkning: jämför med föregående år
- Analysera större avvikelser mot budget
- Periodisera väsentliga intäkter/kostnader

**Bokslutsdispositioner** (section: 'dispositions')
- Periodiseringsfonder: återföring/avsättning
- Överavskrivningar: beräkna enligt huvudregel/kompletteringsregel
- Bokslutsverifikationer: generera och granska

**Årsredovisning** (section: 'annual_report')
- Förvaltningsberättelse: upprätta
- Resultaträkning: upprätta
- Balansräkning: upprätta
- Noter: upprätta
- Kassaflödesanalys: upprätta
- Underskrifter: inhämta styrelsens underskrifter

### Modell: `project.milestone` — används direkt (ingen extend behövs)

Standard-milestones för varje bokslut:
- "Bankavstämning klar" (deadline: bokslutsdatum + 15 dagar)
- "Momsdeklaration Q4 inlämnad" (deadline: 26 feb)
- "SRU genererad" (deadline: 1 juli)
- "Årsredovisning signerad" (deadline: 31 juli)
- "Inskickat till Bolagsverket" (deadline: 31 aug)

Deadlines räknas ut automatiskt baserat på räkenskapsårets slutdatum.

### Dokumentation via chatter + attachments

Ingen separat dokumentationsmodell — istället:
- **Checklistpunkter (tasks)**: Bilagor laddas upp i chattering som bevis på genomförd kontroll (t.ex. avstämnings-PDF, kontoutdrag)
- **Bokslutsverifikationer (account.move)**: Befintlig attachment-funktionalitet för underlag
- **Intern/extern**: Använd Odoos befintliga access rights. Extern dokumentation = exportera valda tasks + bilagor via QWeb-PDF

### Views: Kanban-tavla för checklista

Användarflödet:
1. Gå till Bokslut → klicka "Öppna checklista"
2. Systemet öppnar project.project's Kanban-vy
3. Checklistpunkter visas som kort i kolumner (Att göra / Pågående / Klar)
4. Dra kort mellan kolumner för att uppdatera status
5. Klicka på kort → detaljer: beskrivning, assignee, deadline, bilagor
6. Milstolpar visas i projektets milestone-vy

**Filtrering:**
- Min checklista (assigned to me)
- Per sektion (tagg-filter)
- Endast obligatoriska
- Ej påbörjade / Klara

### QWeb-PDF: Bokslutsdokumentation

En QWeb-rapport (`report/bokslut_dokumentation_pdf.xml`) som exporterar:
- Alla klarmarkerade checklistpunkter med:
  - Datum och användare
  - Eventuella kommentarer
  - Bilagor (infogade i PDF:en)
- Två versioner:
  - **Intern**: Alla punkter + interna kommentarer + alla bilagor
  - **Extern**: Endast valda punkter + externa kommentarer + valda bilagor (filtreras via tag eller checkbox)

---

## Fas 3: Årsredovisningsgenerering

### Modell: `account.annual.report`

En färdig årsredovisning i PDF-format (och ev. PDF/A för Bolagsverket).

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Källa |
| `name` | Char | Namn |
| `fiscalyear_id` | Many2one → account.fiscalyear | Räkenskapsår |
| `company_id` | Many2one → res.company | Företag |
| `rule_set` | Selection | 'K2', 'K3' |
| `content_sections` | Json | Struktur: sektioner med text + tabeller |
| `pdf_report` | Binary | Genererad PDF |
| `pdf_a_report` | Binary | PDF/A för Bolagsverket |
| `state` | Selection | 'draft', 'generated', 'signed', 'submitted' |

**Metoder:**

| Metod | Beskrivning |
|-------|-------------|
| `generate()` | Genererar årsredovisningen från bokslutets data |
| `generate_pdf()` | Renderar QWeb-mall → PDF |
| `generate_pdf_a()` | Konverterar till PDF/A |
| `action_sign()` | Signeringsworkflow |
| `action_submit_bolagsverket()` | Skickar till Bolagsverket (framtida) |

### Innehåll i årsredovisningen

1. **Förvaltningsberättelse** — Auto-genererad text baserat på företagets data (verksamhet, väsentliga händelser, förväntad utveckling)
2. **Resultaträkning** — Från finansiell rapportstruktur (jfr SRU:s r_line_ids)
3. **Balansräkning** — Från finansiell rapportstruktur (jfr SRU:s b_line_ids)
4. **Kassaflödesanalys** — Genereras från kontorörelser (indirekt metod)
5. **Noter** — Redovisningsprinciper, anläggningstillgångar, eget kapital, etc.
6. **Underskrifter** — Plats för styrelsens underskrifter
7. **Fastställelseintyg** — Revisorspåskrift

### Integration med SRU

Årsredovisningen använder samma `account.financial.report`-struktur som `account.sru.declaration`. Data hämtas från:
- `account.sru.declaration` för BR/RR-siffror
- `account.bokslut` för resultatdispositioner och noter
- `account.financial.report` för rapportstruktur (inklusive nivåer, tecken, SRU-koder)

### K2 vs K3

- **K2**: Förenklat regelverk. Färre noter, schablonregler. Mindre företag.
- **K3**: Huvudregelverk. Fler noter, komponentavskrivning, finansiella instrument.

Valet styrs av `rule_set` på `account.annual.report` och påverkar vilka noter och uppställningar som inkluderas.

---

## Fas 4: Periodiseringsfonder + Överavskrivningar

### Periodiseringsfonder

**Koncept:** Företag kan sätta av upp till 25% av vinsten till periodiseringsfond (skjuta upp skatt). Max 6 år innan återföring.

**Modell: `account.periodization_fund` (eller utöka `account.bokslut.adjustment`)**

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Bokslut |
| `year` | Integer | Avsättningsår |
| `amount` | Monetary | Avsatt belopp |
| `remaining` | Monetary | Kvarvarande belopp |
| `reversal_year` | Integer | Senaste återföringsår (max year+6) |
| `state` | Selection | 'active', 'partially_reversed', 'fully_reversed' |

**Logik:**
- POSITIVT resultat → kan avsätta till periodiseringsfond (upp till 25%)
- Återföring sker automatiskt år 6
- Schablonintäkt = statslåneränta × summa periodiseringsfonder (påverkar skatten)

### Överavskrivningar

**Koncept:** Skillnaden mellan bokföringsmässig och skattemässig avskrivning på anläggningstillgångar.

**Modell: `account.excess_depreciation` (eller utöka `account.bokslut.adjustment`)**

| Fält | Typ | Beskrivning |
|------|-----|-------------|
| `bokslut_id` | Many2one → account.bokslut | Bokslut |
| `asset_id` | Many2one → account.asset | Anläggningstillgång |
| `book_depreciation` | Monetary | Planenlig avskrivning |
| `tax_depreciation` | Monetary | Skattemässig avskrivning |
| `difference` | Monetary | Skillnad (över-/underavskrivning) |
| `rule` | Selection | 'huvudregel' (30%), 'kompletteringsregel' (20%) |

**Logik (huvudregeln):**
- Skattemässigt restvärde = IB + inköp - försäljning
- Lägsta tillåtna värde = 70% av skattemässigt restvärde
- Max överavskrivning = bokfört värde - lägsta tillåtna värde

---

## Reuse (befintlig kod att bygga vidare på)

| Befintlig kod | Sökväg | Återanvänds till |
|---------------|--------|-----------------|
| `account.declaration` basklass | `l10n_se_tax_report/models/` | `account.bokslut` — state machine, SKV API, calendar event |
| `account.sru.declaration` | `l10n_se_tax_report/models/sru.py` | Mall för BR/RR-beräkning, SRU-generering |
| `account_fiscalyear` | `l10n_se_tax_report/models/account_fiscalyear.py` | Periodberäkning, räkenskapsår |
| `account.vat.declaration.calculate()` | `l10n_se_tax_report/models/mis_report_generator.py` | MIS-rapportgenerering |
| `account.financial.report` | `l10n_se_account_financial_report` | BR/RR-struktur med sign, nivåer, SRU-koder |
| SKV API-infrastruktur | `l10n_se_tax_report` + `l10n_se_tax_account` | Auth, test/live, API-anrop |
| `mis_builder` | OCA-modul | MIS-rapportinfrastruktur för moms och bokslut |
| `account.period` (account_period_vrtl) | `account_period_vrtl` | Svenska räkenskapsperioder |
| `project.task` + `project.project` | Odoo core `project` | **Kanban-checklista**, stages, milestones, activities |
| `mail.activity` | Odoo core `mail` | Schemalagda påminnelser för bokslut |

---

## Implementation Steps

### Steg 1: Skapa modulstruktur
- [ ] Skapa `l10n_se_bokslut/` med `__init__.py`, `__manifest__.py`
- [ ] Manifest: depends på `l10n_se_tax_report`, `l10n_se_mis`, `l10n_se_account_financial_report`, `l10n_se_extended`
- [ ] `security/ir.model.access.csv` — accessregler för alla nya modeller
- [ ] Registrera i `odoo-l10n_se/.gitignore` om behövs

### Steg 2: Modell `account.bokslut`
- [ ] `models/bokslut_planning.py` — ärver `account.declaration`
- [ ] Alla fält enligt ovan (fiscalyear, period, project_id, adjustments, tax_calcs, etc.)
- [ ] Metoder: `calculate_resultat()`, `calculate_skatt()`, `action_book()`, `action_book_preliminary()`
- [ ] Metod `action_create_checklist_project()` — skapar project.project + kopierar checklist-templates + milestones
- [ ] Metod `action_open_checklist()` — öppnar projektets Kanban-vy
- [ ] `models/__init__.py` — importera bokslut_planning

### Steg 3: Modeller för justeringar och skatteberäkning
- [ ] `models/bokslut_adjustment.py` — `account.bokslut.adjustment`
- [ ] Skatteberäkningsrader inuti `account.bokslut` (in-line) eller separat `account.bokslut.tax.calc`
- [ ] Båda modellerna i `models/__init__.py`

### Steg 4: Views — Bokslutsplanering
- [ ] `views/bokslut_planning_views.xml` — form view med 4 tabs
- [ ] List view + search view
- [ ] Knapp "Öppna checklista" → action_open_checklist()
- [ ] Knapp "Skapa checklista" → action_create_checklist_project()
- [ ] Menu under Myndighetsrapportering (eller egen Bokslut-meny)
- [ ] Action: action_open_bokslut från fiscalyear

### Steg 5: Skatteberäkningslogik
- [ ] Implementera full skatteberäkningskedja i `account.bokslut.calculate_skatt()`
- [ ] Integration med `account.financial.report` för BR/RR-data
- [ ] Stöd för ej avdragsgilla kostnader och ej skattepliktiga intäkter

### Steg 6: Views — Justeringar
- [ ] `views/bokslut_adjustment_views.xml`
- [ ] Form + tree view för justeringar
- [ ] "Lägg till" och "Ta bort" funktionalitet

### Steg 7: Bokslutsverifikationshantering
- [ ] `generate_verifications()` — skapar account.move för resultatdisposition (8999↔2099)
- [ ] Status tracking: Förslag → Preliminär → Bokförd
- [ ] Återanvänd SRU:s befintliga verifikationslogik (`calc_arets_resultat`, `calc_fritt_eget_kapital`)

### Steg 8: Checklista via project.task
- [ ] `models/project_task.py` — extend `project.task` med bokslut_id, section, account_ids, is_required
- [ ] `data/bokslut_task_stages.xml` — stages: Att göra, Pågående, Granskning, Klar, Ej tillämplig
- [ ] `data/bokslut_task_data.xml` — ~50 templates (project.task med `is_template=True`)
- [ ] `views/project_task_views.xml` — extend Kanban + form för bokslutschecklista
- [ ] `views/project_project_views.xml` — extend project.project form (lägg till bokslut_id)
- [ ] `action_create_checklist_project()` — kopierar templates → tasks, skapar milestones, lägger till activities

### Steg 9: Dokumentations-PDF
- [ ] `report/bokslut_dokumentation_pdf.xml` — QWeb-rapport
- [ ] Intern version: alla tasks + bilagor + kommentarer
- [ ] Extern version: valda tasks + valda bilagor

### Steg 10: Årsredovisningsmodell
- [ ] `models/annual_report.py` — `account.annual.report`
- [ ] `generate()` — sammanställer BR, RR, noter från bokslutet
- [ ] `views/annual_report_views.xml`

### Steg 11: QWeb-PDF för årsredovisning
- [ ] `report/annual_report_pdf.xml` — QWeb-mall
- [ ] Layout: försättsblad, förvaltningsberättelse, RR, BR, kassaflöde, noter, underskrifter
- [ ] Stöd för K2 och K3 via `rule_set`

### Steg 12: Bokslutsdokumentation PDF
- [ ] `report/bokslut_dokumentation_pdf.xml` — QWeb-mall
- [ ] Intern version: alla bilagor + kommentarer
- [ ] Extern version: endast valda konton/underlag

### Steg 13: Inställningar
- [ ] `models/res_config.py` — bolagsinställningar (default rule_set, auto-generera checklista)
- [ ] `views/res_config_view.xml` — inställningar i Accounting Configuration

### Steg 14: CRON och påminnelser
- [ ] `data/cron_data.xml` — Påminnelse om bokslut (X dagar före deadline)
- [ ] Auto-skapa bokslut vid nytt räkenskapsår

### Steg 15: Periodiseringsfonder (Fas 4)
- [ ] Modell `account.periodization_fund`
- [ ] Logik: avsättning, återföring, schablonintäkt, 6-årsregel
- [ ] Views + integration med bokslut

### Steg 16: Överavskrivningar (Fas 4)
- [ ] Modell `account.excess_depreciation`
- [ ] Huvudregel (30%) + kompletteringsregel (20%)
- [ ] Views + integration med anläggningsregister och bokslut

### Steg 17: Testning och demo
- [ ] `demo/bokslut_demo.xml` — demo-bokslut med justeringar, checklista, dokumentation
- [ ] Testa hela flödet: Skapa bokslut → justeringar → skatt → verifikationer → årsredovisning

---

## Verifiering

### Funktionsverifiering
1. **Installera** `l10n_se_bokslut` på `scalinq-moms`
2. **Skapa bokslut** för räkenskapsår 2025
3. **Skapa checklista** → action_create_checklist_project() ska skapa ett project.project med ~50 tasks och 5 milestones
4. **Öppna Kanban** → checklistpunkter visas som kort i kolumner (Att göra/Pågående/Klar/Ej tillämplig)
5. **Dra kort** mellan kolumner → stages uppdateras, `date_last_stage_update` sätts
6. **Lägg till bilaga** på en checklistpunkt → chattering fungerar
7. **Kontrollera resultatberäkning** — resultat före bokslut ska matcha kontosaldon 3000-8999
8. **Lägg till justeringar** — ej avdragsgill kostnad, ej skattepliktig intäkt
9. **Verifiera skatteberäkning** — skatten ska vara 20.6% av skattepliktigt resultat
10. **Generera verifikationer** — 8999↔2099 verifikation ska skapas
11. **Preliminärbokför** → slutligt bokför — verifikationer får rätt status
12. **Generera årsredovisning** — PDF med förvaltningsberättelse, BR, RR, noter
13. **Exportera dokumentations-PDF** — intern + extern version

### Kodgranskning
- `shazam_verify --preCommit` ska passera
- Alla modeller har korrekt `_name`, `_description`, `_inherit`
- Accessregler täcker alla modeller
- Views har korrekta xpath-selectors med `@name`

### Fortnox/Visma-jämförelse
- Kan en revisor använda Odoo för bokslut utan att exportera till Fortnox/Visma?
- Kan en redovisningsbyrå hantera flera klienters bokslut?
- Saknas någon väsentlig funktion jämfört med Fortnox Bokslut & Skatt?
