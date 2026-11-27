# Fortnox → Odoo-migrering (l10n_se_migration_fortnox)

Odoo 18+-modul som importerar bokföring från **Fortnox** till Odoo-databasen (`strategy`).

## Översikt

- **Primärväg:** SIE 4 (helhetskopia) – ett anrop hämtar kontoplan, ingående balans och alla verifikationer.
- **Kompletterande:** Fortnox REST API för kunder, leverantörer, artiklar, löner och PDF-fakturor.
- **Säkerhet:** Hemligheter lagras endast i Odoo via `keykeep` – aldrig i källkoden.
- **Idempotens:** Importen kan köras flera gånger utan dubbletter eller obalanser.
- **Dry-run:** Verifiera vad som skulle importeras utan att skriva något.

## Vad kunden måste tillhandahålla

| Fält | Beskrivning |
|------|-------------|
| `fortnox_client_id` | Client ID från Fortnox → Inställningar → Integrationer → API-nycklar |
| `fortnox_client_secret` | Client Secret (samma sida, visas en gång) |
| `fortnox_access_token` | Access Token efter OAuth2 (eller direkt token för Legacy API) |
| `fortnox_refresh_token` *(valfri)* | Refresh token – krävs för automatisk förnyelse (OAuth2) |
| `fortnox_fiscal_year` *(valfri)* | Räkenskapsår, t.ex. `2024`. Tomt = alla år |
| `sie_file` *(valfri)* | SIE 4-fil om du inte vill använda API-verifikationer |

## Så skapar kunden nycklarna

1. Fortnox → **Inställningar** → **Integrationer** → **API-nycklar**.
2. **+ Ny klient** → namn t.ex. "Odoo-migrering (Vertel)".
3. **Tillåten omdirigering:** `https://<odoo-host>/admin/secrets`
4. **Behörighet:** Läs (read) räcker – modulen skriver aldrig tillbaka.
5. Spara → kopiera **Client ID** och **Client Secret**.
6. OAuth2: hämta **Access Token** (+ **Refresh Token**) via Authorization Code-flödet.

## Vad varje fält gör

| Fält | Effekt |
|------|--------|
| `fortnox_client_id` | Identifierar applikationen vid varje API-anrop |
| `fortnox_client_secret` | Hemlig nyckel för token-begäran och förnyelse |
| `fortnox_access_token` | Läser SIE, fakturor, PDF:er, personal, löner |
| `fortnox_refresh_token` | Förnyar Access Token automatiskt när det löper ut |
| `fortnox_fiscal_year` | Begränsar API-verifikationer till ett år (tomt = alla) |
| `sie_file` | Ersätter API-verifikationer med SIE 4-import |

## Arbetsflöde i wizarden

1. **Steg 1** – kontoplan + journaler via `account_resolver` (BAS-intervall).
2. **Steg 2** – kunder, leverantörer, artiklar, personal, lön (API).
3. **Steg 3** – SIE 4 (om aktiverad) skapar IB + verifikationer; annars API-verifikationer.
4. **Steg 4** – PDF:er hämtas och bifogas som `ir.attachment`.
5. **Rapport** – `result_log` och `sie_report` visar antal skapade poster och eventuella fel.

## Säkerhetskontroller

- Fortnox kräver `Access-Token` + `Client-Secret` (inte `Authorization: Bearer`).
- Rate limit 25 req/5 s → backoff inbyggt.
- Idempotens på `(series, number)` för verifikationer.
- Obalanserade verifikationer stoppas; IB/UB valideras.
- Fel loggas, importen avbryts inte av enstaka fel.

## Kända fallgropar

| Problem | Lösning |
|---------|---------|
| SIE-fil i CP437 men Fortnox ger UTF-8 | Parsern provar `utf-8-sig`, `utf-8`, `cp437`, `latin-1` |
| Saknade konton (t.ex. 2080) | `account_resolver` härleder från BAS-intervall eller Fortnox `Type` |
| Saknade journaler (A, B, IB) | `resolve_journal` skapar dem; typ gissas från seriekod |
| Dubbletter vid omimport | Unik nyckel `ref` kontrolleras |
| Leverantörsfaktura-PDF | Bilagekedja `supplierinvoicefileconnections` → `/3/archive/{id}` |
| Access Token löper ut | Förnyas via `refresh_token` och sparas i Odoo |

## Underhåll

- **Version:** `18.0.1.2.0`
- **Logg:** `/var/log/odoo/odoo-server.log` samt `result_log`/`sie_report` i wizarden.

---
*Vertel Sverige AB – 2026-10-25*
