# -*- coding: utf-8 -*-
"""Generera SCB-certifieringstestfiler för Intrastat (INSTAT/XML 6.2).

SCB certifierar programvaruversioner, inte enskilda deklarationer. Bilaga 1
anger vilket testmaterial som ska skickas in: alla meddelandetyper, varierat
innehåll av Intrastatdata och min-/maxvärden för antal tecken i fält. Det här
skriptet bygger den datan och skriver filerna med modulens EGEN generator
(``_generate_xml()``) — inga filer handredigeras, så det som skickas till SCB
är exakt vad en kund får ur Odoo.

Skapa först en scratch-databas (rör aldrig produktionen)::

    odoo -c /etc/odoo/odoo.conf -d intrastat_cert \
        -i l10n_se_intrastat_product --stop-after-init --no-http --without-demo=all

Kör sedan skriptet som odoo-användaren::

    sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d intrastat_cert --no-http \
        < tools/scb_certification_files.py

Allt skapande sker i en transaktion som RULLAS TILLBAKA — databasen lämnas
orörd. Filerna skrivs till /tmp/scb_cert_files/ och valideras mot
static/spec/instat62.xsd. Slutligen kan scratch-databasen droppas::

    sudo -u postgres dropdb intrastat_cert
"""

import os
from datetime import date, timedelta

OUT = os.environ.get("SCB_CERT_OUT", "/tmp/scb_cert_files")
os.makedirs(OUT, exist_ok=True)

env = env  # noqa: F821  (odoo shell)
company = env.company
print("Company:", company.name, company.country_id.code, company.vat)

# --------------------------------------------------------------------------
# 1. Företagsinställningar (svenska Intrastat-krav)
# --------------------------------------------------------------------------
region_ab = env.ref("l10n_se_intrastat_product.intrastat_region_AB")
transport_3 = env.ref("intrastat_product.intrastat_transport_3")
transport_1 = env.ref("intrastat_product.intrastat_transport_1")

# Företagets identitet — samma uppgifter som SFA:s skarpa bolag, så att
# SCB:s kvittens kan matcha organisationen. Inget skickas till SCB härifrån.
company.partner_id.with_context(no_vat_validation=True).write(
    {
        "name": "SFA Sverige AB",
        "vat": "SE556219305101",
        "company_registry": "556219-3051",
        "street": "Box 797",
        "zip": "191 27",
        "city": "Sollentuna",
    }
)

company.write(
    {
        "intrastat_arrivals": "extended",
        "intrastat_dispatches": "extended",
        "intrastat_region_id": region_ab.id,
        "intrastat_transport_id": transport_3.id,
        "intrastat_contact_name": "Anders Wallenquist",
        "intrastat_contact_phone": "08-123456",
        "intrastat_contact_email": "anders.wallenquist@vertel.se",
    }
)

# --------------------------------------------------------------------------
# 2. Momskod för EU-varuhandel (så att fiskal position blir b2b)
# --------------------------------------------------------------------------
Tax = env["account.tax"]
tax_sale = Tax.search(
    [("type_tax_use", "=", "sale"), ("amount", "=", 0), ("company_id", "=", company.id)],
    limit=1,
)
if not tax_sale:
    tax_sale = Tax.create(
        {
            "name": "EU-varor 0%",
            "amount": 0.0,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "company_id": company.id,
        }
    )
tax_purchase = Tax.search(
    [("type_tax_use", "=", "purchase"), ("amount", "=", 0), ("company_id", "=", company.id)],
    limit=1,
)
if not tax_purchase:
    tax_purchase = Tax.create(
        {
            "name": "EU-varor inköp 0%",
            "amount": 0.0,
            "amount_type": "percent",
            "type_tax_use": "purchase",
            "company_id": company.id,
        }
    )

# --------------------------------------------------------------------------
# 3. Fiskala positioner: b2b (varor) och b2c (privatpersoner)
# --------------------------------------------------------------------------
FiscalPos = env["account.fiscal.position"]
fp_b2b = FiscalPos.create(
    {
        "name": "EU B2B varor (Intrastat)",
        "intrastat": "b2b",
        "vat_required": True,
        "country_group_id": env.ref("base.europe").id,
        "auto_apply": True,
        "company_id": company.id,
    }
)
fp_b2c = FiscalPos.create(
    {
        "name": "EU B2C varor (Intrastat)",
        "intrastat": "b2c",
        "vat_required": False,
        "country_group_id": env.ref("base.europe").id,
        "company_id": company.id,
    }
)

# --------------------------------------------------------------------------
# 4. Enheter: styck (PCE) och kilogram (KGM) som tilläggsenheter
# --------------------------------------------------------------------------
IntrastatUnit = env["intrastat.unit"]
uom_unit = env.ref("uom.product_uom_unit")
uom_kg = env.ref("uom.product_uom_kgm")
unit_pce = IntrastatUnit.search([("name", "=", "PCE")], limit=1) or IntrastatUnit.create(
    {"name": "PCE", "description": "Antal styck", "uom_id": uom_unit.id}
)
unit_kgm = IntrastatUnit.search([("name", "=", "KGM")], limit=1) or IntrastatUnit.create(
    {"name": "KGM", "description": "Vikt i kilogram", "uom_id": uom_kg.id}
)

# --------------------------------------------------------------------------
# 5. HS-koder (CN8) — blandade med och utan tilläggsenhet
# --------------------------------------------------------------------------
HSCode = env["hs.code"]
HS_CODES = [
    ("84137081", unit_pce),   # pumpar — styck
    ("85099000", unit_pce),   # delar till hushållsmaskiner — styck
    ("84818099", unit_pce),   # ventiler — styck
    ("39174000", unit_pce),   # rördelar av plast — styck
    ("73181588", unit_kgm),   # skruv/bult — kilogram
    ("85444290", unit_pce),   # ledningar — styck
]
hs = {}
for code, unit in HS_CODES:
    rec = HSCode.search([("local_code", "=", code)], limit=1)
    if not rec:
        rec = HSCode.create(
            {
                "local_code": code,
                "description": f"Testvara CN8 {code}",
                "intrastat_unit_id": unit.id,
            }
        )
    else:
        rec.intrastat_unit_id = unit.id
    hs[code] = rec

# --------------------------------------------------------------------------
# 6. Produkter — vikt per enhet, ursprungsland, Intrastat-typ
# --------------------------------------------------------------------------
Product = env["product.product"]
PRODUCTS = [
    # (artikelkod, namn, hs-kod, vikt kg/st, ursprungsland, tilläggsenhet)
    ("CERT-PUMP-01", "CERT Avloppspump 400 W", "84137081", 12.5, "SE", True),
    ("CERT-PUMP-02", "CERT Avloppspump 800 W", "84137081", 21.0, "DE", True),
    ("CERT-PART-01", "CERT Kretskort styrenhet", "85099000", 0.85, "CN", True),
    ("CERT-PART-02", "CERT Packningssats", "85099000", 0.35, "IT", True),
    ("CERT-VALVE-01", "CERT Backventil DN50", "84818099", 3.2, "PL", True),
    ("CERT-PIPE-01", "CERT Rörböj 110 mm", "39174000", 0.9, "NL", True),
    ("CERT-SCREW-01", "CERT Skruv M8x60", "73181588", 0.05, "DE", True),
    ("CERT-CABLE-01", "CERT Anslutningskabel 3 m", "85444290", 1.4, "FR", True),
]
products = {}
for code, name, hscode, weight, origin, has_su in PRODUCTS:
    p = Product.search([("default_code", "=", code)], limit=1)
    if not p:
        p = Product.create(
            {
                "name": name,
                "default_code": code,
                "type": "consu",
                "is_storable": True,
                "weight": weight,
                "origin_country_id": env["res.country"].search(
                    [("code", "=", origin)], limit=1
                ).id,
                "standard_price": 100.0,
                "list_price": 200.0,
                "taxes_id": [(6, 0, [tax_sale.id])],
                "supplier_taxes_id": [(6, 0, [tax_purchase.id])],
            }
        )
    # HS-kod sätts på produktmallen (local_code är det fält som används)
    p.product_tmpl_id.hs_code_id = hs[hscode].id
    products[code] = p

# --------------------------------------------------------------------------
# 7. Partner — olika länder, med och utan VAT (B2C), långa namn
# --------------------------------------------------------------------------
Partner = env["res.partner"]
Country = env["res.country"]
PARTNERS = [
    # (namn, land, vat, är_företag)
    ("Testbolaget Norden AB", "DE", "DE554854973", True),
    ("Testbolaget Frankrike SARL", "FR", "FR45751999301", True),
    ("Testbolaget Nederländerna BV", "NL", "NL630065494B01", True),
    ("Testbolaget Italien SRL", "IT", "IT95331131201", True),
    ("Testbolaget Polen SP ZOO", "PL", "PL3106012301", True),
    ("Testbolaget Spanien SL", "ES", "ESB12345674", True),
    ("Testbolaget Danmark A/S", "DK", "DK41415592", True),
    ("Testbolaget Finland OY", "FI", "FI29372131", True),
    ("Testbolaget Österrike GmbH", "AT", "ATU42994195", True),
    ("Testbolaget Belgien NV", "BE", "BE689523906", True),
    ("Testbolaget Portugal LDA", "PT", "PT151639078", True),
    ("Testbolaget Tjeckien SRO", "CZ", "CZ474307380", True),
    ("Testbolaget Grekland AE", "GR", "GR421858485", True),
    ("Testbolaget Ungern KFT", "HU", "HU39708973", True),
    ("Testbolaget Rumänien SRL", "RO", "RO113049532", True),
    ("Testbolaget Irland LTD", "IE", "IE5520328AB", True),
    ("Testbolaget Slovenien DOO", "SI", "SI95061258", True),
    ("Testbolaget Kroatien DOO", "HR", "HR22052644001", True),
    ("Testbolaget Luxemburg SA", "LU", "LU57092579", True),
    ("Privatperson Tyskland", "DE", False, False),
    ("Privatperson Frankrike", "FR", False, False),
    ("Privatperson Nederländerna", "NL", False, False),
    # Extremvärden för teckenlängd — SCB vill se min- och maxvärden
    (
        "Europeiska Distributions- och Logistikaktiebolaget Skandinavien "
        "Försäljning Syd GmbH",
        "DE",
        "DE554854973",
        True,
    ),
    ("Å", "DK", "DK41415592", True),
]
partners = {}
for name, ccode, vat, is_company in PARTNERS:
    country = Country.search([("code", "=", ccode)], limit=1)
    p = Partner.search([("name", "=", name)], limit=1)
    if not p:
        p = Partner.with_context(no_vat_validation=True).create(
            {
                "name": name,
                "is_company": is_company,
                "company_type": "company" if is_company else "person",
                "country_id": country.id,
                "vat": vat or False,
                "country_id": country.id,
                "street": "Testgatan 1",
                "zip": "12345",
                "city": "Teststad",
                "email": "test@example.com",
            }
        )
    partners[name] = p

# --------------------------------------------------------------------------
# 8. Fakturor
# --------------------------------------------------------------------------
Move = env["account.move"]
MONTH = "11"
YEAR = "2026"
BASE_DATE = date(2026, 11, 3)


def make_invoice(
    move_type,
    partner,
    lines,
    inv_date,
    transaction=None,
    transport=None,
    fp=None,
    currency=None,
):
    """lines: lista av (produkt, antal, pris)."""
    vals = {
        "move_type": move_type,
        "partner_id": partner.id,
        "invoice_date": inv_date,
        "date": inv_date,
        "company_id": company.id,
        "intrastat_transaction_id": transaction.id if transaction else False,
        "intrastat_transport_id": transport.id if transport else False,
        "invoice_line_ids": [
            (
                0,
                0,
                {
                    "product_id": prod.id,
                    "quantity": qty,
                    "price_unit": price,
                    "tax_ids": [
                        (
                            6,
                            0,
                            [
                                (
                                    tax_sale
                                    if move_type.startswith("out")
                                    else tax_purchase
                                ).id
                            ],
                        )
                    ],
                },
            )
            for prod, qty, price in lines
        ],
    }
    if fp:
        vals["fiscal_position_id"] = fp.id
    if currency:
        vals["currency_id"] = currency.id
    return Move.create(vals)


T = env["intrastat.transaction"]
t11 = env.ref("intrastat_product.intrastat_transaction_11")
t12 = env.ref("intrastat_product.intrastat_transaction_12")
t21 = env.ref("intrastat_product.intrastat_transaction_21")
t22 = env.ref("intrastat_product.intrastat_transaction_22")
t23 = env.ref("intrastat_product.intrastat_transaction_23")
t51 = env.ref("intrastat_product.intrastat_transaction_51")
t52 = env.ref("intrastat_product.intrastat_transaction_52")
t91 = env.ref("intrastat_product.intrastat_transaction_91")
t99 = env.ref("intrastat_product.intrastat_transaction_99")

invoices = []

# --- UTFÖRSEL (dispatches) ------------------------------------------------
# 1. B2B, flera länder, flera HS-koder, olika transportmedel
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Norden AB"],
        [
            (products["CERT-PUMP-01"], 10, 2450.00),
            (products["CERT-PART-01"], 25, 780.50),
        ],
        BASE_DATE,
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Frankrike SARL"],
        [(products["CERT-PUMP-02"], 4, 3980.00)],
        BASE_DATE + timedelta(days=2),
        transaction=t11,
        transport=transport_1,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Nederländerna BV"],
        [
            (products["CERT-VALVE-01"], 120, 145.75),
            (products["CERT-PIPE-01"], 300, 39.90),
        ],
        BASE_DATE + timedelta(days=3),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 2. B2C (privatperson) — transaktion 12, ingen VAT
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Privatperson Tyskland"],
        [(products["CERT-PUMP-01"], 1, 2995.00)],
        BASE_DATE + timedelta(days=4),
        transaction=t12,
        transport=transport_3,
        fp=fp_b2c,
    )
)
# 3. Retur (kreditfaktura) — transaktion 21
invoices.append(
    make_invoice(
        "out_refund",
        partners["Testbolaget Italien SRL"],
        [(products["CERT-PART-02"], 5, 420.00)],
        BASE_DATE + timedelta(days=5),
        transaction=t21,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 4. Ersättning utan retur — transaktion 23
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Polen SP ZOO"],
        [(products["CERT-PART-02"], 3, 420.00)],
        BASE_DATE + timedelta(days=6),
        transaction=t23,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 5. Varor efter bearbetning — transaktion 51
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Spanien SL"],
        [(products["CERT-SCREW-01"], 5000, 2.10)],
        BASE_DATE + timedelta(days=7),
        transaction=t51,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 6. Operationell leasing — transaktion 91, min-värde
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Danmark A/S"],
        [(products["CERT-CABLE-01"], 1, 0.01)],
        BASE_DATE + timedelta(days=8),
        transaction=t91,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 7. Övrigt — transaktion 99, max-värde (stor summa)
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Testbolaget Finland OY"],
        [(products["CERT-PUMP-02"], 200, 3980.00)],
        BASE_DATE + timedelta(days=9),
        transaction=t99,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# 8. Övriga länder (täcker landskoder)
for idx, name in enumerate(
    [
        "Testbolaget Österrike GmbH",
        "Testbolaget Belgien NV",
        "Testbolaget Portugal LDA",
        "Testbolaget Tjeckien SRO",
        "Testbolaget Grekland AE",
        "Testbolaget Ungern KFT",
        "Testbolaget Rumänien SRL",
        "Testbolaget Irland LTD",
        "Testbolaget Slovenien DOO",
        "Testbolaget Kroatien DOO",
        "Testbolaget Luxemburg SA",
    ]
):
    invoices.append(
        make_invoice(
            "out_invoice",
            partners[name],
            [(products["CERT-PART-01"], 10 + idx, 780.50)],
            BASE_DATE + timedelta(days=10 + idx),
            transaction=t11,
            transport=transport_3,
            fp=fp_b2b,
        )
    )

# 9. Extremvärden — lägsta och högsta fakturavärde/kvantitet i samma fil
invoices.append(
    make_invoice(
        "out_invoice",
        partners[
            "Europeiska Distributions- och Logistikaktiebolaget Skandinavien "
            "Försäljning Syd GmbH"
        ],
        [(products["CERT-PART-02"], 1, 0.01)],
        BASE_DATE + timedelta(days=21),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "out_invoice",
        partners["Å"],
        [(products["CERT-PUMP-02"], 5000, 1999.99)],
        BASE_DATE + timedelta(days=22),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)

# --- INFÖRSEL (arrivals) --------------------------------------------------
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Norden AB"],
        [
            (products["CERT-PUMP-02"], 6, 3100.00),
            (products["CERT-PART-02"], 40, 310.00),
        ],
        BASE_DATE + timedelta(days=1),
        transaction=t11,
        transport=transport_1,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Frankrike SARL"],
        [(products["CERT-CABLE-01"], 50, 129.00)],
        BASE_DATE + timedelta(days=2),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Nederländerna BV"],
        [(products["CERT-PIPE-01"], 400, 34.50)],
        BASE_DATE + timedelta(days=3),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Italien SRL"],
        [(products["CERT-VALVE-01"], 80, 128.00)],
        BASE_DATE + timedelta(days=4),
        transaction=t11,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# Retur till leverantör — 21
invoices.append(
    make_invoice(
        "in_refund",
        partners["Testbolaget Polen SP ZOO"],
        [(products["CERT-SCREW-01"], 1000, 1.95)],
        BASE_DATE + timedelta(days=5),
        transaction=t21,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# Ersättning från leverantör — 22
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Spanien SL"],
        [(products["CERT-PART-01"], 15, 690.00)],
        BASE_DATE + timedelta(days=6),
        transaction=t22,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# Varor för bearbetning — 52
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Testbolaget Danmark A/S"],
        [(products["CERT-PUMP-01"], 12, 2100.00)],
        BASE_DATE + timedelta(days=7),
        transaction=t52,
        transport=transport_3,
        fp=fp_b2b,
    )
)
# B2C-införsel — 12
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Privatperson Frankrike"],
        [(products["CERT-PART-02"], 2, 500.00)],
        BASE_DATE + timedelta(days=8),
        transaction=t12,
        transport=transport_3,
        fp=fp_b2c,
    )
)
invoices.append(
    make_invoice(
        "in_invoice",
        partners["Privatperson Nederländerna"],
        [(products["CERT-VALVE-01"], 2, 195.00)],
        BASE_DATE + timedelta(days=9),
        transaction=t12,
        transport=transport_3,
        fp=fp_b2c,
    )
)

for inv in invoices:
    inv.action_post()

print("Fakturor skapade:", len(invoices))

# --------------------------------------------------------------------------
# 9. Deklarationer
# --------------------------------------------------------------------------
Decl = env["intrastat.product.declaration"]


def build(decl_type, month, action, revision=1, level="extended"):
    d = Decl.create(
        {
            "company_id": company.id,
            "declaration_type": decl_type,
            "year": YEAR,
            "month": month,
            "action": action,
            "revision": revision,
        }
    )
    d.action_gather()
    d.draft2confirmed()
    return d


decls = {}
# Fil 1: utförsel, ny rapport (O), extended
d = build("dispatches", MONTH, "append")
decls["dispatch"] = d
print("Utförsel:", len(d.computation_line_ids), "beräknade /",
      len(d.declaration_line_ids), "deklarationsrader")

# Fil 2: införsel, ny rapport (O), extended
d2 = build("arrivals", MONTH, "append")
decls["arrival"] = d2
print("Införsel:", len(d2.computation_line_ids), "beräknade /",
      len(d2.declaration_line_ids), "deklarationsrader")

# Fil 3: utförsel, standard (declarationTypeCode 2)
d3 = build("dispatches", MONTH, "append", revision=2)
d3.reporting_level = "standard"
d3.draft2confirmed() if False else None
decls["dispatch_standard"] = d3

# Fil 4: utförsel, ersättning (R)
d4 = build("dispatches", MONTH, "replace", revision=3)
decls["dispatch_replace"] = d4

# Fil 5: införsel, ersättning (R) — kontaktperson med svenska tecken (Å Ä Ö)
# så att filen bevisar att ISO 8859-1-kodningen håller hela vägen ut.
company.write({"intrastat_contact_name": "Åsa Öberg Ärlig"})
d5 = build("arrivals", MONTH, "replace", revision=2)
decls["arrival_replace"] = d5

# Fil 6: utförsel, nollrapport (N) — ingen faktura i perioden
d6 = Decl.create(
    {
        "company_id": company.id,
        "declaration_type": "dispatches",
        "year": "2026",
        "month": "12",
        "action": "nihil",
        "revision": 1,
    }
)
d6.action_gather()
d6.draft2confirmed()
decls["nihil"] = d6
print("Nollrapport:", len(d6.declaration_line_ids), "rader (ska vara 0)")

# --------------------------------------------------------------------------
# 10. Generera XML med modulens egen generator
# --------------------------------------------------------------------------
from lxml import etree  # noqa: E402

xsd_path = "/usr/share/odoo-l10n_se/l10n_se_intrastat_product/static/spec/instat62.xsd"
schema = etree.XMLSchema(etree.parse(xsd_path))

written = []
for key, decl in decls.items():
    xml = decl._generate_xml()
    fn = f"{decl.year}-{decl.month}_{decl.declaration_type}_{decl.action}_{key}.xml"
    path = os.path.join(OUT, fn)
    with open(path, "wb") as fh:
        fh.write(xml)
    doc = etree.fromstring(xml)
    ok = schema.validate(doc)
    errs = "\n".join(f"  line {e.line}: {e.message}" for e in schema.error_log)
    written.append((fn, len(xml), ok, errs))
    print(f"{fn}: {len(xml)} bytes, XSD {'OK' if ok else 'FEL'}")
    if not ok:
        print(errs)

# --------------------------------------------------------------------------
# 11. Rulla tillbaka — databasen lämnas orörd
# --------------------------------------------------------------------------
env.cr.rollback()
print("ROLLBACK klar — databasen orörd. Filer i", OUT)
