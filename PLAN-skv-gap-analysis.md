# Analys: Odoo svensk lokalisering — vad saknas?

En kartläggning av odoo-l10n_se + odoo-l10n_se_payroll mot Skatteverkets API:er
och funktionalitet hos Fortnox, Visma och Business Central.

## Sammanfattning

Odoos svenska lokalisering (Vertels `odoo-l10n_se` + `odoo-l10n_se_payroll`) är
**imponerande komplett** för ett open source-system. Den täcker redan moms, AGD,
periodisk sammanställning, SRU, SIE, OCR, bankgiro/plusgiro, skattekontoavstämning
och en fullfjädrad lönehantering med FK-integration, kollektivavtal,
arbetsgivarintyg och tidrapportering.

De viktigaste luckorna finns inom tre områden:

| # | Område | Värde | Ansträngning |
|---|--------|-------|-------------|
| 1 | **AGI (individuppgifter) — SKV API** | 🔴 Kritiskt | Medel |
| 2 | **Årsredovisning + Bolagsverket** | 🟠 Högt | Hög |
| 3 | **PEPPOL e-faktura (in/ut)** | 🟠 Högt | Medel |
| 4 | **Inkomstdeklaration 2-4 via SKV API** | 🟡 Medium | Medel |
| 5 | **Skattekonto — huvudmän/ombud** | 🟡 Medium | Låg |
| 6 | **Automatiska bankflöden** | 🟡 Medium | Hög |
| 7 | **Bilförmån via SKV API** | 🟢 Låg | Låg |
| 8 | **Fråga om skatteavdrag (SKV API)** | 🟢 Låg | Låg |

---

## 1. Vad som redan finns (baseline)

### odoo-l10n_se (detta repo — 24 moduler)

| Modul | Funktion | SKV API? |
|-------|----------|----------|
| `l10n_se_extended` | BAS 2021 kontoplan (K1-K4), organisationsnummer | Nej |
| `l10n_se_tax_report` | Momsdeklaration, AGD, Periodisk sammanställning | ✅ Ja (moms, agd, pc) |
| `l10n_se_tax_account` | Skattekontoavstämning — hämta transaktioner + 2-kolumns avstämning | ✅ Ja |
| `l10n_se_sie` | SIE-import/export (full) | Nej |
| `l10n_se_sie_minimal` | SIE-import (minimal) | Nej |
| `l10n_se_ocr` / `_reconcile` | OCR-nummer, inläsning av leverantörsfakturor | Nej |
| `l10n_se_account_bank_statement_import` | Import av kontoutdrag (Swedbank, SEB, etc.) | Nej |
| `l10n_se_credit_transfer` | Bankgiro/Plusgiro betalningar (ISO 20022) | Nej |
| `l10n_se_account_payment_order` | Betalningsformat (bankgiro, utlandsbetalning) | Nej |
| `l10n_se_bank` | Basmodul för bankdrivrutiner | Nej |
| `l10n_se_fiscal_position` | Svenska fiskala positioner | Nej |
| `l10n_se_intrastat_product` | Intrastat-rapportering till SCB | Nej |
| `l10n_se_kommun` / `_municipality_class` | Kommunkoder, kommunklassning | Nej |
| `l10n_se_mis` / `_mis_kommun` | MIS-rapportmallar för svensk redovisning | Nej |
| `l10n_se_date_ranges` | Räkenskapsperioder (account_period_vrtl) | Nej |
| `l10n_se_tax_display_name` | Svensk formatering av momsnamn | Nej |
| `l10n_se_account_financial_report` | Finansiella rapporter | Nej |

### SKV API-integration som redan finns

| API | Modul | Status |
|-----|-------|--------|
| Momsdeklaration v2 | `l10n_se_tax_report` | ✅ Implementerad (cert + e-leg) |
| Arbetsgivardeklaration v2 | `l10n_se_tax_report` | ✅ Implementerad |
| Periodisk sammanställning | `l10n_se_tax_report` | ✅ Implementerad |
| Skattekonto — transaktioner | `l10n_se_tax_account` | ✅ Implementerad |

### odoo-l10n_se_payroll (14 moduler)

| Modul | Funktion | SKV API? |
|-------|----------|----------|
| `l10n_se_hr_payroll` | Kärnmodul: lönekörning, skatteregler, rapporter | Delvis (skattetabell) |
| `l10n_se_hr_holidays` | Svensk semesterhantering | Nej |
| `l10n_se_hr_payroll_account` | Lön → bokföring | Nej |
| `l10n_se_hr_payroll_fk` | Försäkringskassan (sjuk, VAB, föräldraledig) | Nej |
| `l10n_se_hr_payroll_collective` | Kollektivavtal | Nej |
| `l10n_se_hr_payroll_flex` | Flextidsavstämning | Nej |
| `l10n_se_hr_payroll_benefits` | Förmåner | Nej |
| `l10n_se_hr_payroll_tiichri` | Tidrapportering (TiiChri) | Nej |
| `l10n_se_hr_payroll_tiichri_26` | TiiChri för 2026 | Nej |
| `l10n_se_payroll_taxtable` | Skattetabeller från SKV (öppna data) | ✅ Ja (öppna data) |
| `l10n_se_payroll_sn_report` | SCB:s lönerapportering | Nej |
| `l10n_se_arbetsgivarintyg` | Digitala arbetsgivarintyg (arbetsgivarintyg.nu) | ✅ Ja (SOAP) |
| `l10n_se_hr_holidays_account` | Semesterlöneskuld bokföring | Nej |

---

## 2. Skatteverkets API:er — fullständig lista

Källa: [Skatteverket — Auktorisationsflöden per API](https://www.skatteverket.se/omoss/digitalasamarbeten/borjaanvandaapier/auktorisationsflodenperapi.4.7da1d2e118be03f8e4f8246.html)

### Redan integrerade ✅

| API | Typ | Odoo-modul |
|-----|-----|------------|
| Momsdeklaration | Partner | `l10n_se_tax_report` |
| Arbetsgivardeklaration - inlämning | Partner | `l10n_se_tax_report` |
| Arbetsgivardeklaration - hantera redovisningsperiod | Partner | `l10n_se_tax_report` |
| Skattekonto | Partner | `l10n_se_tax_account` |

### EJ integrerade — med relevans för Odoo ❌

| API | Typ | Relevans | Prioritet |
|-----|-----|----------|-----------|
| **Arbetsgivardeklaration - individuppgifter (AGI)** | Partner | 🔴 Kritisk — månatlig rapportering av alla anställdas löner och skatter. Utan denna kan Odoo inte ersätta ett lönesystem fullt ut. | 1 |
| **Inkomstdeklaration 1 (INK1)** | Partner | 🟡 Medium — privatpersoners deklaration. Kan användas av redovisningsbyråer för att hjälpa kunder. | 5 |
| **Inkomstdeklaration 2-4 (INK2-4)** | Partner | 🟠 Hög — företagens inkomstdeklaration. SRU-modulen genererar redan blanketter men skickar inte via API. | 3 |
| **Skattekonto - hämta huvudmäns saldo** | Partner | 🟡 Medium — för redovisningsbyråer med många klienter. l10n_se_tax_account gör detta för ett företag men saknar multi-klient vy. | 4 |
| **Fråga om skatteavdrag** | Partner | 🟢 Låg — hämta preliminärskatt för anställd. Kan ersätta manuell skattetabellsuppslagning. | 7 |
| **Fråga om skatteavdrag i kronor** | Partner | 🟢 Låg — samma som ovan, men svarar i SEK. | 8 |
| **Beskattningsengagemang** | Partner | 🟢 Låg — användbart för byråer som hanterar många företag. | 9 |
| **Beslutade skatteuppgifter** | Partner | 🟡 Medium — auto-importera taxeringsbeslut. Minskar manuellt arbete. | 6 |
| **Bilförmån** | Partner | 🟢 Låg — hämta förmånsvärde för tjänstebil automatiskt istället för manuell inmatning. | 7 |
| **Kundhändelser** | Partner | 🟢 Låg — spåra ärenden hos SKV. | 10 |
| **Ombudshantering** | Partner | 🟡 Medium — för byråer. Hantera ombudsroller via API istället för SKV:s webb. | 6 |

---

## 3. Fortnox funktionalitet — vad kan Odoo lära?

Fortnox är marknadsledande för små/medelstora företag i Sverige. Deras styrkor:

| Funktion | Beskrivning | Odoo-status |
|----------|-------------|-------------|
| **Automatisk bokföring från kontoutdrag** | Banktransaktioner matchas automatiskt mot fakturor, löner, etc. via AI-regelverk | ⚠️ Delvis — bankimport finns men kräver manuell filuppladdning |
| **PEPPOL e-faktura** | Skicka/ta emot e-fakturor direkt i systemet | ❌ Saknas (finns OCA-moduler men ej integrerade) |
| **Snabbfakturering med autokontering** | Förifyllda konteringsmallar per kund/leverantör/produkt | ⚠️ Delvis — Odoo har produkter och kontomallar men ej svensk-specifika |
| **Årsredovisning** | Generera årsredovisning och skicka till Bolagsverket | ❌ Saknas |
| **Löneintegration** | Inbyggd integration med Fortnox Lön | ✅ Odoo har egen lön via l10n_se_payroll |
| **Momsredovisning** | Automatisk momsredovisning med direktinlämning | ✅ Finns via l10n_se_tax_report |
| **RUT/ROT-hantering** | Automatisk hantering av RUT/ROT-avdrag | ❌ Saknas |

**Viktigaste att lägga till:** Automatisk bankavstämning + PEPPOL + Årsredovisning.

---

## 4. Business Central — svensk lokalisering

Från Microsofts dokumentation:

| Funktion | BC-status | Odoo-status |
|----------|-----------|-------------|
| Automatic Account Codes | ✅ Finns | ⚠️ Delvis (produkt-kontomallar) |
| SIE Import/Export | ✅ Finns | ✅ Finns |
| EU Third-Party Purchase (VAT) | ✅ Finns | ⚠️ Delvis (fiscal positions) |
| VAT Reporting | ✅ Finns | ✅ Finns |
| Payment Time Reporting (stora företag) | ✅ Finns | ❌ Saknas |
| Bankgiro/Plusgiro | ✅ Finns | ✅ Finns |

**Viktigaste att lägga till:** Payment time reporting (lagkrav för stora företag) och Automatic Account Codes.

---

## 5. Rekommenderade prioriteringar

### 🔴 PRIO 1 — AGI (individuppgifter) via SKV API

**Varför:** Utan AGI kan Odoo inte fullt ut konkurrera med Fortnox Lön/Visma Lön.
Alla arbetsgivare måste lämna individuppgifter varje månad. Idag görs detta
antingen manuellt på SKV:s webb eller via ett separat lönesystem.

**Vad krävs:**
- Ny modul: `l10n_se_agi` (eller utöka `l10n_se_tax_report`)
- API: `Arbetsgivardeklaration - individuppgifter`
- Auth: Client Credentials (org-legitimation) eller Authorization Code (e-leg)
- Mappa payslip-rader → AGI-fält (lön, skatt, förmåner, etc.)
- Periodhantering via `Arbetsgivardeklaration - hantera redovisningsperiod`
- Integration med `l10n_se_hr_payroll` för att auto-populera data

**Arbetsinsats:** 2-3 veckor (API:t är relativt enkelt, jobbet är mappning + testning)

---

### 🟠 PRIO 2 — Årsredovisning + Bolagsverket

**Varför:** Alla aktiebolag måste lämna årsredovisning. Fortnox och Visma har
inbyggt stöd för att generera och skicka till Bolagsverket. Odoo har finansiella
rapporter men ingen färdig årsredovisningsmall.

**Vad krävs:**
- Ny modul: `l10n_se_annual_report`
- Rapportmallar enligt BFNAR/K3-regelverket
- Generering av PDF med rätt struktur (förvaltningsberättelse, resultaträkning, balansräkning, noter)
- PDF/A-konvertering för Bolagsverket
- Ev. integration med Bolagsverkets e-tjänst (om API finns)
- SRU-export (finns redan)

**Arbetsinsats:** 4-6 veckor (komplex rapportering + juridisk korrekthet)

---

### 🟠 PRIO 3 — PEPPOL e-faktura

**Varför:** PEPPOL är standard för e-faktura i Sverige och obligatoriskt för
offentlig sektor. Fortnox och Visma har inbyggt stöd.

**Vad krävs:**
- Ny modul: `l10n_se_peppol` (eller anpassa OCA:s `edi_peppol`)
- PEPPOL Access Point-anslutning
- Svensk PEPPOL BIS Billing 3.0-profil
- Hantering av svenska formatkrav (org.nr, bankgiro, plusgiro, etc.)
- Inläsning av inkommande PEPPOL-fakturor → leverantörsfaktura

**Arbetsinsats:** 2-3 veckor (om OCA-modul används som bas, annars 4-6 veckor)

---

### 🟡 PRIO 4 — Inkomstdeklaration 2-4 via SKV API

**Varför:** SRU-modulen genererar redan blanketterna. Att skicka direkt via API
skulle spara tid och minska fel.

**Vad krävs:**
- Utöka `l10n_se_tax_report`/`sru.py`
- API: `Inkomstdeklaration 2-4`
- Auth: Client Credentials (org-legitimation) eller Authorization Code (e-leg)
- Mappa SRU-fält → API-payload

**Arbetsinsats:** 1-2 veckor (API-förbrukning är relativt enkel)

---

### 🟡 PRIO 5 — Skattekonto huvudmän (multi-klient)

**Varför:** Redovisningsbyråer hanterar 50-500 företag. Idag måste de logga in
var för sig. Med "huvudmän"-API:et kan en byrå hämta alla klienters skattekonton
i ett anrop.

**Vad krävs:**
- Utöka `l10n_se_tax_account`
- Stöd för ombudsrollen
- Multi-company vy för skattekonto
- Batch-hämtning av transaktioner

**Arbetsinsats:** 1-2 veckor

---

### 🟡 PRIO 6 — Beslutade skatteuppgifter + Beskattningsengagemang

**Varför:** Auto-importera SKV:s beslut (taxering, moms, etc.) istället för
manuell registrering. Särskilt värdefullt för redovisningsbyråer.

**Arbetsinsats:** 1-2 veckor

---

### 🟢 PRIO 7 — Fråga om skatteavdrag / Bilförmån

**Varför:** Mindre features som ger "polish". Skatteavdrag kan användas för att
validera/dubbelkolla skattetabeller. Bilförmån auto-populerar förmånsvärden.

**Arbetsinsats:** 2-3 dagar vardera

---

## 6. Saker Fortnox/Visma/BC har som Odoo inte har

| Funktion | Prioritet | Kommentar |
|----------|-----------|-----------|
| Automatisk bankavstämning med AI | 🟡 Medium | Kräver bank-API:er (PSD2), stort projekt |
| Årsredovisning till Bolagsverket | 🟠 Hög | Se PRIO 2 ovan |
| PEPPOL e-faktura | 🟠 Hög | Se PRIO 3 ovan |
| RUT/ROT-hantering | 🟡 Medium | Kräver Skatteverket RUT/ROT-API (finns ej som partner-API än) |
| Payment time reporting | 🟢 Låg | Endast för stora företag (>250 anställda) |
| Automatic Account Codes (konteringsmallar) | 🟢 Låg | Odoo har redan kontomallar, kan förbättras |

---

## 7. Implementation roadmap (rekommenderad ordning)

```
Vecka 1-3:   AGI (individuppgifter) — PRIO 1 🔴
Vecka 4-6:   PEPPOL e-faktura — PRIO 3 🟠
Vecka 7-10:  Årsredovisning — PRIO 2 🟠
Vecka 11-12: Inkomstdeklaration 2-4 API — PRIO 4 🟡
Vecka 13-14: Skattekonto huvudmän — PRIO 5 🟡
Vecka 15-16: Beslutade skatteuppgifter — PRIO 6 🟡
Vecka 17-19: Fråga om skatteavdrag + Bilförmån — PRIO 7 🟢
```

**Total estimerad insats:** ~4-5 månader för allt ovan, eller ~6-8 veckor för
de tre högst prioriterade (AGI + PEPPOL + Inkomstdeklaration API).

---

## 8. Slutsats

Odoo med Vertels `odoo-l10n_se` + `odoo-l10n_se_payroll` är redan ett av de mest
kompletta open source-alternativen för svensk redovisning och lönehantering.
Systemet hanterar moms, AGD, SRU, SIE, OCR, bankbetalningar och har en
fullfjädrad lönehantering.

**Den enskilt viktigaste funktionen som saknas är AGI (individuppgifter) —**
den månatliga rapporteringen av anställdas löner till Skatteverket. Utan denna
är Odoos lönesystem inte "complete" ur ett svenskt perspektiv — användaren
måste fortfarande gå till SKV:s webb eller ha ett separat lönesystem för att
fullgöra sin rapporteringsskyldighet.

Därefter kommer PEPPOL e-faktura (krav för offentlig sektor) och årsredovisning
(alla aktiebolag behöver det).

De övriga SKV API:erna (inkomstdeklaration, skattekonto huvudmän, beslutade
skatteuppgifter, bilförmån) är "nice to have" som skulle ge Odoo en
konkurrensfördel jämfört med Fortnox/Visma, men är inte kritiska.
