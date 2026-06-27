# PLAN: `l10n_se_fleet_benefit` — Bilförmån från Skatteverket via Fleet

## Context

Svenska arbetsgivare måste rapportera bilförmån som skattepliktig förmån på
den anställdes lönespecifikation. Förmånsvärdet bestäms av Skatteverket och
beror på bilens nybilspris, extrautrustning, drivmedel, miljöklassning etc.

Idag görs detta manuellt:
1. Användaren slår upp förmånsvärdet på `skatteverket.se/bilforman`
2. Skapar manuellt en `hr.contract.benefit` med rätt värde

Med denna modul hämtas förmånsvärdet direkt från SKV:s API för
`fleet.vehicle` och synkas automatiskt till lönesystemet.

## Reuse — befintligt att bygga på

| Komponent | Fil/Modul | Vad den ger |
|-----------|-----------|-------------|
| `res.partner` SKV-fält | `l10n_se_tax_account/models/partner.py` | `enable_skatteverket_api`, `oauth_client_id`, `oauth_secret`, `access_token`, `certificate` |
| SKV API-token-hämtning | `l10n_se_tax_report/models/moms.py::_get_skv_access_token()` | Hämtar OAuth2 access_token via client_credentials |
| SKV auth controller | `l10n_se_tax_account/controllers/skatteverket_auth.py` | OAuth2 callback för e-leg (behövs ej för bilförmån — den använder client_credentials) |
| SKV company settings | `l10n_se_tax_report/models/res_config.py` | `skv_test_mode`, `skv_auth_method`, API URL endpoints |
| `fleet.vehicle` | `core-odoo/fleet/models/fleet_vehicle.py` | `license_plate`, `driver_id`, `model_id`, `fuel_type`, `co2`, `acquisition_date` |
| `hr.contract.benefit` | `l10n_se_hr_payroll_benefits/models/hr_contract.py` | `contract_id`, `name` (hr.benefit), `value`, `date_start`, `date_end` |
| `hr.benefit` | `l10n_se_hr_payroll_benefits/models/hr_contract.py` | `name` (kod), `desc`, `code_id` (löneregel), `category` |

## SKV Bilförmån API

- **Version:** 2.0.x
- **Auth:** Client Credential Grant (endast client_id + client_secret — ingen org-legitimation krävs)
- **Test endpoint:** `https://test.api.skatteverket.se/bilforman/v2/`
- **Produktion:** `https://api.skatteverket.se/bilforman/v2/`
- **Input (troligt):** `registreringsnummer` (license plate) → API → förmånsvärde, nybilspris, etc.
- **Alternativ input:** `modellkod` + extrautrustning (men registreringsnummer är enklast för fleet)

Notera: Den exakta request/response-strukturen måste verifieras mot SKV:s API-konsol
när API-nycklar finns. Vi designar för `GET /v2/foremal/{registreringsnummer}` eller
`POST /v2/berakna` med `{registreringsnummer: "ABC123"}`.

## Approach

En lättviktsmodul som:
1. **Extendar `fleet.vehicle`** med knapp "Hämta förmånsvärde" och fält för cachat värde
2. **SKV API-klient** — anropar Bilförmån-API med registreringsnummer
3. **Synk till lön** — skapar/uppdaterar `hr.contract.benefit` för fordonets förare
4. **Company-inställningar** — test/prod endpoint + API-credentials

## Files to create

```
l10n_se_fleet_benefit/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── fleet_vehicle.py          # Extend fleet.vehicle — SKV integration
│   ├── res_company.py            # Company settings (skv_bilforman_* fields)
│   └── res_config_settings.py    # Settings UI
├── views/
│   ├── fleet_vehicle_views.xml   # "Hämta förmånsvärde" button + fields
│   └── res_config_settings.xml   # API endpoint config
├── security/
│   └── ir.model.access.csv
├── data/
│   └── hr_benefit_data.xml       # Default "Bilförmån" benefit type
└── static/description/
    └── icon.png
```

## Steps

- [ ] 1. **Skapa modulstruktur** — `__manifest__.py`, `__init__.py`, kataloger
  - Manifest: `depends=['fleet', 'l10n_se_hr_payroll_benefits', 'l10n_se_tax_account']`
  
- [ ] 2. **Company settings** (`models/res_company.py` + `res_config_settings.py`)
  - `skv_bilforman_test_mode` (Boolean, default True)
  - `skv_bilforman_api_url` (Char, computed based on test_mode)
  - `skv_bilforman_scope` (Char, default 'bilforman')
  - Återanvänd `skv_auth_method`, `skv_auth_url`, `skv_token_url` från l10n_se_tax_report
  - Default endpoint: `https://test.api.skatteverket.se/bilforman/v2` / `https://api.skatteverket.se/bilforman/v2`

- [ ] 3. **Extend fleet.vehicle** (`models/fleet_vehicle.py`)
  - Fields:
    - `benefit_value` (Float) — månatligt förmånsvärde från SKV
    - `benefit_nybilspris` (Float) — nybilspris från SKV
    - `benefit_extra_utrustning` (Float) — extrautrustning
    - `benefit_miljobil` (Boolean) — miljöbil?
    - `benefit_fetched_date` (Datetime) — senast hämtat
    - `benefit_applied` (Boolean) — är värdet synkat till lön?
  - Methods:
    - `action_fetch_benefit()` — anropar SKV API, sparar resultat
    - `_get_skv_benefit_client()` — bygger API-klient med token
    - `action_apply_to_payroll()` — skapar/uppdaterar hr.contract.benefit
    - `_find_employee_contract()` — hittar anställds aktiva kontrakt via driver_id

- [ ] 4. **SKV API-klient** (i `fleet_vehicle.py` eller separat `api_client.py`)
  - Återanvänd `_get_skv_partner()` och `_get_skv_access_token()` från moms.py-mönstret
  - `requests.get/post()` till `skv_bilforman_api_url/foremal/{regnummer}`
  - Parse JSON response → `benefit_value`, `nybilspris`, etc.
  - Felhantering: UserError om bilen inte hittas, API-fel etc.

- [ ] 5. **Default förmånstyp** (`data/hr_benefit_data.xml`)
  - Skapa `hr.benefit` med `name='BILFOR'`, `desc='Bilförmån'`, `category='vehicle'`
  - Gör den tillgänglig för auto-population

- [ ] 6. **Views**
  - `fleet_vehicle_views.xml`: Lägg till en flik/sektion "SKV Bilförmån" med:
    - Knapp "Hämta förmånsvärde"
    - Visning av `benefit_value`, `benefit_nybilspris`, `benefit_fetched_date`
    - Knapp "Applicera på lön" (synk till hr.contract.benefit)
  - `res_config_settings.xml`: Bilförmån-inställningar (test mode, endpoint overrides)

- [ ] 7. **Security**
  - `ir.model.access.csv` — om nya modeller skapas (troligen ej nödvändigt om vi bara extendar)

- [ ] 8. **Testa mot SKV test-API**
  - Behöver API-nycklar (client_id + client_secret) från SKV
  - Testa med kända registreringsnummer (t.ex. från testdata)
  - Verifiera att rätt förmånsvärde returneras
  - Verifiera att värdet synkas korrekt till hr.contract.benefit

- [ ] 9. **Edge cases & felhantering**
  - Bilen har ingen förare → visa varning, spara värdet ändå
  - Föraren har inget aktivt kontrakt → spara, visa "väntar på kontrakt"
  - API:t returnerar "bilen hittas inte" → UserError med förklaring
  - Redan applicerat värde ska inte dubbleras → uppdatera existerande benefit
  - Tomt registreringsnummer → validera innan API-anrop

- [ ] 10. **Dokumentation**
  - README i modulen
  - Uppdatera `PLAN-skv-gap-analysis.md` med status

## Verification

1. **Installera modulen** på `scalinq-moms` databasen
2. **Skapa ett fleet.vehicle** med registreringsnummer `ABC123` (test-regnummer)
3. **Konfigurera SKV API** via Settings → Bilförmån (lägg in test-credentials)
4. **Klicka "Hämta förmånsvärde"** → verifiera att API-anrop går igenom och värdet visas
5. **Koppla en förare** (res.partner med hr.employee + aktivt kontrakt)
6. **Klicka "Applicera på lön"** → verifiera att `hr.contract.benefit` skapas med rätt värde
7. **Kör lönekörning** → verifiera att bilförmånen syns på lönespecen
8. **Testa edge cases:** bil utan förare, bil utan kontrakt, ogiltigt regnummer, API-nere

## Open questions

1. **Exakt API-struktur** — endpoint path, request/response format måste verifieras
   via SKV:s API-konsol när vi har API-nycklar. Planen antar `GET /v2/foremal/{regnummer}`
   men det kan vara `POST` eller annan path.
2. **Ska modulen ligga i `odoo-l10n_se` eller `odoo-l10n_se_payroll`?**
   Den behöver `fleet` (core) + `l10n_se_hr_payroll_benefits` (payroll) + SKV API (l10n_se).
   Förslagsvis i `odoo-l10n_se` eftersom den är främst en SKV-integration — men
   `odoo-l10n_se_payroll` är också rimligt eftersom målet är lönekoppling.
   → **Rekommendation:** `odoo-l10n_se` (bredare användning, fleet är core)
3. **Ska vi stödja manuell override?** Om användaren vill ange ett annat värde
   än det SKV returnerar (t.ex. vid reducerad förmån pga. privat körjournal).
   → Ja, `benefit_value` ska vara editable.
