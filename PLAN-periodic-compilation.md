# Plan: Förbättra periodisk sammanställning + API + kalender

## Sammanfattning av nuvarande kodläge

Modulen `l10n_se_tax_report` hanterar tre myndighetsrapporter:
- **Momsdeklaration** (`account.vat.declaration`) — har redan: Skatteverket API, kalenderhändelse, cron, eSKD XML
- **Periodisk sammanställning** (`account.periodic.compilation`) — saknar: SKV API, kalenderhändelse, cron
- **SRU-deklaration** (`account.sru.declaration`) — specialfall, ej i scope nu

Alla tre ärver från `account.declaration` (bas i `models/moms.py`). Basen har redan:
- `event_id` (Many2one → `calendar.event`)
- `create_event()` — skapar kalenderhändelse med `categ_accounting`
- `_calculate_vat_deadline()` — beräknar deadline med `workalendar` (svenska helgdagar)
- `create()` / `write()` triggar automatiskt `create_event()` när `date` sätts

**Skatteverket API finns redan implementerat för momsdeklarationen** i `models/mis_report_generator.py`:
- `skv_api_status`, `skv_response`, `skv_submitted_date` — fält på `account.vat.declaration`
- `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()` — hjälpmetoder
- `action_send_to_skv()` — skicka eSKD XML till Skatteverket via API med certifikat
- Konfiguration i `res.company`: `skv_test_mode`, `skv_auth_method`, `skv_api_url`, `skv_auth_url`, `skv_token_url`

---

## Problem och förbättringar

### 1. Förbättra periodisk sammanställning

| Problem | Idag | Mål |
|---|---|---|
| **A. Deadline på helger** | `date = date_stop + timedelta(days=12)` — ignorerar helgdagar | Använd `_calculate_vat_deadline()` från basklassen (redan implementerad, använder `workalendar`) |
| **B. `date` sätts via onchange** | `@api.onchange('date_start', 'date_stop')` triggas inte vid create/write från kod | Ersätt med `@api.depends` så att date alltid beräknas |
| **C. Ingen nedladdningsknapp** | `pc_file` visas som binärt fält i formuläret | Lägg till en nedladdningsknapp (Odoo-standard binary download) |
| **D. Filtrering på `invoice_date`** | Endast `invoice_date` används i `_get_period_invoices()` | Behåll som idag — standardbeteende, kan utökas senare |
| **E. VFEU hantering** | `calculate()` matchar VTEU, FTEU, 3FEU för periodisk sammanställning (korrekt: det är en försäljningslista) | Ingen ändring — logiken är korrekt |
| **F. Ingen cron** | Momsdeklaration har `_cron_create_vat_declaration()`, periodisk saknar | Lägg till `_cron_create_periodic_compilation()` |
| **G. Kalenderhändelse saknas** | `create_event()` triggas inte tillförlitligt för periodisk sammanställning | Fixa så att `date` sätts konsekvent (se B), lägg till kalenderknapp i formuläret |

### 2. Skatteverket API för periodisk sammanställning

**Återanvänd befintlig infrastruktur (DRY):**

| Komponent | Var den finns idag | Åtgärd |
|---|---|---|
| SKV API-fält (`skv_api_status`, `skv_response`, `skv_submitted_date`) | `account.vat.declaration` | **Flytta till basklassen** `account.declaration` så alla ärver |
| `action_send_to_skv()` | `account.vat.declaration` | Behåll moms-specifik, **lägg till separat implementation** i `account.periodic.compilation` |
| SKV-inställningar | `res.company` — redan gemensamma | Återanvänds direkt |
| `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()` | `account.vat.declaration` | **Flytta till basklassen** `account.declaration` |

**Filformat:**
- Momsdeklaration → eSKD XML (finns)
- Periodisk sammanställning → SKV5740 semikolonseparerad text (finns som `generate_pc_file()`)
- Båda skickas via Skatteverkets API, men kan ha olika endpoints

### 3. Deklarationsdatum i kalendern

| Problem | Åtgärd |
|---|---|
| `create_event()` triggas inte korrekt | Fixa `date`-beräkningen (se 1.B) så att basklassens `write()` triggar `create_event` |
| Inget kalenderevent syns i formuläret | Lägg till kalender-knapp i formuläret som öppnar `event_id` |
| Kalendervyn finns redan | `view_periodic_calendar` — fungerar, ingen ändring behövs |

---

## Implementation

### Steg 1: Flytta SKV API-fält och hjälpmetoder till basklassen

**Fil:** `models/moms.py` — lägg till på `account.declaration`:

Fält som flyttas från `mis_report_generator.py`:
- `skv_api_status` (Selection: draft/submitted/accepted/error)
- `skv_response` (Text)
- `skv_submitted_date` (Datetime)

Hjälpmetoder som flyttas från `mis_report_generator.py`:
- `_get_skv_settings()` → returnerar dict med test_mode, auth_method, api_url, auth_url, token_url
- `_get_skv_partner()` → hittar partner med `enable_skatteverket_api=True`
- `_get_skv_access_token(partner)` → OAuth2 client_credentials med certifikat

Ta bort dessa fält och metoder från `account.vat.declaration` i `mis_report_generator.py`.

### Steg 2: Lägg till separat API-endpoint för periodisk sammanställning med test/live-toggle

**Fil:** `models/res_config.py` — lägg till på `res.company`:

```python
skv_pc_api_url = fields.Char(
    string='SKV PC API URL',
    help="Skatteverket API endpoint for periodic compilation (EU sales list).")

def _compute_skv_pc_api_url(self):
    """Beräkna default endpoint baserat på test/live-mode."""
    for company in self:
        if not company.skv_pc_api_url:
            if company.skv_test_mode:
                company.skv_pc_api_url = 'https://test.api.skatteverket.se/moms/v2/periodsammandrag'
            else:
                company.skv_pc_api_url = 'https://api.skatteverket.se/moms/v2/periodsammandrag'
```

Lägg även till `skv_pc_api_url` i `ResConfigSettings` (related, readonly=False) så den syns i inställningarna.

**Fil:** `views/res_config_view.xml` — lägg till:
```xml
<setting id="skv_pc_api_url" help="Endpoint for submitting periodic compilations" title="SKV PC API URL" groups="account.group_account_user">
    <field name="skv_pc_api_url"/>
</setting>
```

Användaren kan:
- Bocka i/ur `skv_test_mode` → default-URL växlar automatiskt mellan test och produktion
- Manuellt ändra `skv_pc_api_url` om Skatteverket uppdaterar sina endpoints

---

### Steg 3: Uppgradera pc_file från SKV5740 till eSKD XML

**Fil:** `models/periodic_compilation.py` — ersätt `generate_pc_file()`

Idag producerar `generate_pc_file()` en semikolonseparerad textfil (SKV5740-format). Ersätt med eSKD XML (samma DTD som momsdeklarationen, `eSKDUpload 6.0`):

```python
def generate_pc_file(self):
    for rec in self:
        rec.pc_file = None
        root = etree.Element('eSKDUpload', Version="6.0")
        orgnr = etree.SubElement(root, 'OrgNr')
        orgnr.text = rec.company_id.company_registry or ''
        
        ps = etree.SubElement(root, 'PeriodiskSammanstallning')
        period = etree.SubElement(ps, 'Period')
        period.text = fields.Date.from_string(rec.date_start).strftime('%Y%m')
        
        for line in rec.line_ids:
            partner_el = etree.SubElement(ps, 'Kopare')
            vat_el = etree.SubElement(partner_el, 'VATNr')
            vat_el.text = line.partner_id.vat or ''
            
            if line.pc_supplied_goods:
                goods = etree.SubElement(partner_el, 'LevereradeVaror')
                goods.text = str(int(round(line.pc_supplied_goods)))
            if line.pc_triangulation:
                triang = etree.SubElement(partner_el, 'Trepartshandel')
                triang.text = str(int(round(line.pc_triangulation)))
            if line.pc_services_supplied:
                services = etree.SubElement(partner_el, 'TillhandahallnaTjanster')
                services.text = str(int(round(line.pc_services_supplied)))
        
        xml_bytes = etree.tostring(root, pretty_print=True, encoding='ISO-8859-1')
        xml_str = xml_bytes.decode('ISO-8859-1')
        xml_str = xml_str.replace('?>', '?>\n<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www.skatteverket.se/download/18.3f4496fd14864cc5ac99cb1/1415022101213/eSKDUpload_6p0.dtd">')
        rec.pc_file = base64.b64encode(xml_str.encode('ISO-8859-1'))
        rec.pc_file_name = 'periodisk_sammanstallning_%s.xml' % fields.Date.from_string(rec.date_start).strftime('%y%m')
```

**Importera:** `from lxml import etree` (finns redan i `moms.py`, behöver läggas till i `periodic_compilation.py`).

---

### Steg 4: Lägg till `action_send_to_skv()` för periodisk sammanställning

**Fil:** `models/periodic_compilation.py`

Implementera `action_send_to_skv()` som:
1. Säkerställer att `pc_file` finns (anropar `generate_pc_file()` vid behov)
2. Hämtar partner och access token via basklassens metoder
3. Skickar eSKD XML-filen till Skatteverket via `requests.post` mot `company.skv_pc_api_url`
4. Hanterar svar (accepted/error) och uppdaterar `skv_api_status`, `skv_response`, `skv_submitted_date`
5. Hanterar 401 (token expired) — rensar token och visar felmeddelande

### Steg 5: Fixa `date`-beräkning (deadline + kalender)

**Fil:** `models/periodic_compilation.py`

Ersätt `@api.onchange('date_start', 'date_stop')` med:

```python
@api.depends('date_start', 'date_stop')
def _compute_date_and_name(self):
    for rec in self:
        if rec.date_start and rec.date_stop:
            rec.name = '%s %s - %s' % (rec._report_name, rec.date_start, rec.date_stop)
            rec.date = rec._calculate_vat_deadline(
                fields.Date.from_string(rec.date_stop), 1)
```

Gör `name` och `date` till computed fields (med `store=True`) istället för att sättas via onchange.

**Varför:** `@api.onchange` triggas bara i UI. `@api.depends` + computed/store triggas alltid. Basklassens `create()`/`write()` kommer då att se `date` i values och trigga `create_event()`.

### Steg 6: Lägg till "Skicka till Skatteverket"-knapp + API-flik i vyn

**Fil:** `views/periodic_compilation.xml`

Lägg till i `<header>`:
```xml
<button class="oe_highlight" 
    invisible="state not in ['confirmed','done'] or skv_api_status not in ['draft','error']" 
    name="action_send_to_skv" 
    string="Skicka till Skatteverket" 
    type="object"/>
<field name="skv_api_status" 
    invisible="skv_api_status == 'draft'" 
    widget="badge" 
    decoration-success="skv_api_status == 'accepted'" 
    decoration-danger="skv_api_status == 'error'" 
    decoration-warning="skv_api_status == 'submitted'"/>
```

Lägg till ny flik i `<notebook>`:
```xml
<page string="Skatteverket API" invisible="skv_api_status == 'draft' and not skv_response">
    <group>
        <field name="skv_api_status"/>
        <field name="skv_submitted_date"/>
        <field name="skv_response" nolabel="1" invisible="skv_api_status != 'error'"/>
    </group>
</page>
```

### Steg 7: Lägg till nedladdningsknapp för pc_file

**Fil:** `models/periodic_compilation.py` — ny metod:
```python
def action_download_pc_file(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_url',
        'url': '/web/content/%s/%s/pc_file/%s?download=true' % (
            self._name, self.id, self.pc_file_name),
        'target': 'self',
    }
```

**Fil:** `views/periodic_compilation.xml` — ersätt råa fältet med:
```xml
<field name="pc_file" filename="pc_file_name" invisible="1"/>
<button class="oe_stat_button" icon="fa-download" 
    name="action_download_pc_file" type="object" 
    string="Ladda ner" invisible="state == 'draft' or not pc_file"/>
```

### Steg 8: Lägg till kalender-knapp i formuläret

**Fil:** `models/periodic_compilation.py` — ny metod:
```python
def action_open_calendar_event(self):
    self.ensure_one()
    if self.event_id:
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'res_id': self.event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
```

**Fil:** `views/periodic_compilation.xml` — lägg till i `button_box`:
```xml
<button class="oe_stat_button" icon="fa-calendar" 
    name="action_open_calendar_event" type="object" 
    string="Kalender" invisible="not event_id"
    help="Öppna kalenderhändelsen för deklarationsdatum"/>
```

### Steg 9: Lägg till cron för automatisk skapande

**Fil:** `data/cron_data.xml` — ny post:
```xml
<record id="ir_cron_periodic_compilation" model="ir.cron">
    <field name="name">Periodisk sammanställning: create next period</field>
    <field name="model_id" ref="model_account_periodic_compilation"/>
    <field name="state">code</field>
    <field name="code">model._cron_create_periodic_compilation()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="priority" eval="5"/>
</record>
```

**Fil:** `models/periodic_compilation.py` — ny metod:
```python
@api.model
def _cron_create_periodic_compilation(self):
    last = self.search([], order='date_stop desc', limit=1)
    if last:
        date_start = fields.Date.from_string(last.date_stop) + timedelta(days=1)
    else:
        today = fields.Date.today()
        date_start = today.replace(day=1)
    date_stop = date_start + relativedelta(months=1, days=-1)
    existing = self.search([
        ('date_start', '>=', date_start),
        ('date_stop', '<=', date_stop),
    ], limit=1)
    if existing:
        return False
    deadline = self._calculate_vat_deadline(date_stop, 1)
    self.create({
        'date_start': fields.Date.to_string(date_start),
        'date_stop': fields.Date.to_string(date_stop),
        'date': fields.Date.to_string(deadline),
    })
```

---

## Filer att modifiera

| Fil | Ändring |
|---|---|
| `models/moms.py` | + SKV API-fält (`skv_api_status`, `skv_response`, `skv_submitted_date`) på `account.declaration`, + `_get_skv_settings()`, `_get_skv_partner()`, `_get_skv_access_token()` |
| `models/mis_report_generator.py` | − SKV API-fält (flyttade till bas), − SKV-hjälpmetoder (flyttade till bas), behåll moms-specifik `action_send_to_skv()` |
| `models/res_config.py` | + `skv_pc_api_url` på `res.company` (med test/live default), + related-fält i `ResConfigSettings` |
| `models/periodic_compilation.py` | + `action_send_to_skv()`, + `_cron_create_periodic_compilation()`, + `action_download_pc_file()`, + `action_open_calendar_event()`, ersätt `onchange` → `@api.depends` för date/name, ersätt `generate_pc_file()` med eSKD XML-format |
| `views/periodic_compilation.xml` | + "Skicka till Skatteverket"-knapp, + SKV API-flik, + nedladdningsknapp, + kalender-knapp |
| `views/res_config_view.xml` | + `skv_pc_api_url`-fält under Skatteverket API-sektionen |
| `data/cron_data.xml` | + `<record id="ir_cron_periodic_compilation">` |
| `security/ir.model.access.csv` | Ev. behövs access för `account.periodic.compilation` till SKV-fälten (ärvs från `account.declaration`, bör vara OK) |
| `tests/test_periodic_compilation.py` | + Test för `date`-beräkning (helgdagar), + Test för eSKD XML-generering, + Test för `action_send_to_skv()` (mock), + Test för kalenderhändelse |

---

## Återanvändning av befintlig kod

| Befintlig funktion | Plats | Återanvänds för |
|---|---|---|
| `_calculate_vat_deadline()` | `models/moms.py` → `account.declaration` | Korrekt deadline (helgdagar) för periodisk sammanställning |
| `create_event()` | `models/moms.py` → `account.declaration` | Kalenderhändelse — triggas via `create()`/`write()` |
| `_get_skv_settings()` | `models/mis_report_generator.py` | Flyttas till bas, används av båda |
| `_get_skv_partner()` | `models/mis_report_generator.py` | Flyttas till bas, används av båda |
| `_get_skv_access_token()` | `models/mis_report_generator.py` | Flyttas till bas, används av båda |
| `generate_pc_file()` | `models/periodic_compilation.py` | Redan implementerad, återanvänds i `action_send_to_skv()` |
| `skv_*` fält på `res.company` | `models/res_config.py` | Redan gemensamma, ingen ändring |
| `categ_accounting` | `data/account_data.xml` | Redan definierad, används av `create_event()` |
| `view_periodic_calendar` | `views/periodic_compilation.xml` | Redan implementerad — visar date i kalendervy |

---

## Verifiering

1. **Deadline:** Skapa periodisk sammanställning → `date` är en vardag (ej helg/röd dag)
2. **Kalender:** Öppna kalendervyn → deklarationsdatum syns som "Accounting Report"-händelse
3. **Kalender-knapp:** I formuläret → "Kalender"-knapp öppnar `calendar.event`
4. **SKV-knapp:** Efter `calculate()` → "Skicka till Skatteverket" skickar filen till API
5. **Nedladdning:** Efter `calculate()` → "Ladda ner" laddar ner eSKD XML-fil (inte SKV5740)
6. **Test/live-toggle:** I Inställningar → bocka i/ur `skv_test_mode` → `skv_pc_api_url` växlar mellan test- och produktions-URL
7. **Cron:** Cron skapar automatiskt nästa periods periodiska sammanställning
8. **Bakåtkompatibilitet:** `test_periodic_compilation.py` (6 testfall) ska passera — testfallen kontrollerar `pc_file` (formatet ändras men fil ska finnas)
9. **Momsdeklaration oförändrad:** `action_send_to_skv()` för moms fungerar efter fältflytt
10. **Importera `requests` och `lxml`:** `periodic_compilation.py` måste importera `requests` och `from lxml import etree`

---

## Risker och öppna frågor

1. **`name` och `date` som computed fields** — om de görs computed/store kan det påverka existerande flöden där man manuellt ändrar `date`. Bör utredas om `date` ska vara helt computed eller editable med smart default.
