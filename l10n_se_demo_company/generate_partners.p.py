#!/usr/bin/env python3
"""Generate anonymised demo partners from the SFA production database.

Reads the partners that actually have invoices in 2024-2027, replaces every
identifying field (name, org number, VAT, address, bank giro) with invented
data, and writes an XML data file for l10n_se_demo_company.

The structure is preserved: same number of customers and suppliers, the same
customer/supplier split, and company-vs-person distribution. Only the
identities change.
"""
import hashlib
import os
import subprocess
import sys

# The SFA database is only reachable over SSH on that host, not over TCP
# from here. The query is run through ssh and the rows are read from stdin
# instead — see fetch_rows() below.
SSH_HOST = '192.168.11.145'
SSH_DB = 'odoo-sfa-ce-18-se-production'

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data', 'partners.xml')

# Invented company names. Deterministic order, no relation to the source.
COMPANY_WORDS = [
    'Nordkap', 'Berglind', 'Sjöhaga', 'Fjällmark', 'Stenbro', 'Vitsippa',
    'Granlund', 'Havsörn', 'Kvarnvik', 'Lindbacke', 'Örtagård', 'Svedjemo',
    'Tornfallet', 'Vindskydd', 'Ängsmark', 'Björkdal', 'Cederskog', 'Duvholm',
    'Ekbacken', 'Furuvik', 'Grankulla', 'Hedlunda', 'Isdala', 'Junibacken',
    'Kilfors', 'Ljusdal', 'Mossberg', 'Norrsken', 'Ormberg', 'Pilgård',
    'Rimforsa', 'Solvik', 'Timrå', 'Ulvsjö', 'Vallmo', 'Ytterby',
    'Åkerslund', 'Älvdal', 'Ödeshög', 'Storfors', 'Lillhamra', 'Mellby',
    'Sörgården', 'Norrgården', 'Västanvik', 'Östanfors', 'Mittåsen',
    'Högfors', 'Låglanda', 'Bredvik',
]
COMPANY_SUFFIX = [
    'AB', 'AB', 'AB', 'AB', 'Sverige AB', 'Nordic AB', 'Gruppen AB',
    'Teknik AB', 'Service AB', 'Partner AB', 'Industri AB', 'Handel AB',
]

FIRST_NAMES = [
    'Alva', 'Bengt', 'Cecilia', 'Dan', 'Elin', 'Folke', 'Greta', 'Håkan',
    'Ines', 'Jonas', 'Kajsa', 'Lars', 'Maja', 'Nils', 'Olga', 'Per',
    'Qarin', 'Rolf', 'Sara', 'Tore', 'Ulla', 'Viktor', 'Wilma', 'Yngve',
    'Åsa', 'Ärling', 'Örjan', 'Beata', 'Casper', 'Dagny', 'Evert', 'Frida',
    'Göran', 'Hedvig', 'Ivar', 'Josefin', 'Klas', 'Lovisa', 'Magnus', 'Nora',
    'Oskar', 'Petra', 'Rasmus', 'Signe', 'Tobias', 'Ulrika', 'Valter', 'Ylva',
    'Åke', 'Örjan', 'Bertil', 'Carina', 'Douglas', 'Ebba', 'Filip', 'Gunilla',
    'Henrik', 'Isabella', 'Joakim', 'Kristina', 'Leif', 'Monica', 'Niklas',
]
LAST_NAMES = [
    'Ahlberg', 'Bergström', 'Cederlund', 'Dahlgren', 'Eklund', 'Falk',
    'Grenholm', 'Hedberg', 'Isaksson', 'Jonsson', 'Kallström', 'Lindqvist',
    'Malmberg', 'Nordström', 'Olausson', 'Palmgren', 'Qvist', 'Rydell',
    'Sandberg', 'Thorsell', 'Udd', 'Vesterlund', 'Wahlgren', 'Ytterberg',
    'Åkerlind', 'Ängqvist', 'Öberg', 'Bäckman', 'Cronvall', 'Dufva',
    'Engvall', 'Forsell', 'Gustafsson', 'Hultgren', 'Ivarsson', 'Jernberg',
    'Kvarnström', 'Lundell', 'Moberg', 'Nyström',
]

CITIES = [
    ('Stockholm', '111 20'), ('Göteborg', '411 03'), ('Malmö', '211 20'),
    ('Uppsala', '753 20'), ('Västerås', '721 30'), ('Örebro', '702 10'),
    ('Linköping', '582 20'), ('Helsingborg', '252 20'), ('Jönköping', '553 20'),
    ('Norrköping', '602 20'), ('Lund', '221 00'), ('Umeå', '903 20'),
    ('Gävle', '802 50'), ('Borås', '501 10'), ('Södertälje', '151 20'),
    ('Eskilstuna', '632 20'), ('Halmstad', '302 30'), ('Växjö', '352 30'),
    ('Karlstad', '651 80'), ('Sundsvall', '852 30'),
]

STREETS = [
    'Industrivägen', 'Verkstadsgatan', 'Handelsvägen', 'Norra Strandgatan',
    'Södra Esplanaden', 'Fabriksgatan', 'Lagervägen', 'Kontorsvägen',
    'Bergsgatan', 'Sjövägen', 'Järnvägsgatan', 'Storgatan', 'Skolgatan',
    'Parkvägen', 'Björkallén', 'Ekvägen', 'Hantverkargatan', 'Smedjegatan',
]


def stable_int(key, modulo):
    """Deterministic index from a key — same source always maps the same way."""
    h = hashlib.sha256(key.encode('utf-8')).hexdigest()
    return int(h[:12], 16) % modulo


def _luhn_check_digit(digits):
    """Swedish org numbers use the Luhn algorithm over the first 9 digits."""
    total = 0
    for i, ch in enumerate(digits):
        d = int(ch)
        # Positions alternate: double every other digit starting from the first
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def fake_orgnr(key):
    """Invented but Luhn-valid Swedish org number, 556xxx-xxxx."""
    base = f"556{stable_int(key + 'org', 10 ** 7):07d}"  # 10 digits, last is check
    first9 = base[:9]
    check = _luhn_check_digit(first9)
    return f"{first9[:6]}-{first9[6:]}{check}"


def fake_vat(key):
    """VAT number: SE + the 10 org number digits + 01. No extra check digit."""
    orgnr = fake_orgnr(key).replace('-', '')  # 10 digits
    return 'SE' + orgnr + '01'                # 12 digits after SE


def fake_bankgiro(key):
    n = stable_int(key + 'bg', 10 ** 8)
    return f"{n:08d}"[:7] + '-' + f"{n:08d}"[7:]


def fake_name(key, is_company):
    if is_company:
        w = COMPANY_WORDS[stable_int(key + 'w', len(COMPANY_WORDS))]
        s = COMPANY_SUFFIX[stable_int(key + 's', len(COMPANY_SUFFIX))]
        return f"{w} {s}"
    f = FIRST_NAMES[stable_int(key + 'f', len(FIRST_NAMES))]
    l = LAST_NAMES[stable_int(key + 'l', len(LAST_NAMES))]
    return f"{f} {l}"


def fake_address(key):
    street = STREETS[stable_int(key + 'st', len(STREETS))]
    num = 1 + stable_int(key + 'nr', 180)
    city, zipc = CITIES[stable_int(key + 'c', len(CITIES))]
    return street, str(num), zipc, city


def xml_escape(s):
    if s is None:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


QUERY = """
        SELECT rp.id, rp.name, rp.is_company,
               (SELECT count(*) FROM account_move am
                  WHERE am.partner_id = rp.id
                    AND am.move_type = 'out_invoice'
                    AND am.date >= '2023-10-01' AND am.date < '2028-01-01') AS n_customer,
               (SELECT count(*) FROM account_move am
                  WHERE am.partner_id = rp.id
                    AND am.move_type = 'in_invoice'
                    AND am.date >= '2023-10-01' AND am.date < '2028-01-01') AS n_supplier
        FROM res_partner rp
        WHERE rp.id IN (
            SELECT DISTINCT partner_id FROM account_move
            WHERE move_type IN ('out_invoice', 'in_invoice')
              AND partner_id IS NOT NULL
              AND date >= '2023-10-01' AND date < '2028-01-01')
        ORDER BY rp.id
"""


def fetch_rows():
    """Run the query over ssh and parse the pipe-separated output."""
    sql = QUERY.replace('"', '\\"').replace('\n', ' ')
    cmd = [
        'ssh', '-o', 'ConnectTimeout=10', SSH_HOST,
        f'sudo -n -u postgres psql -d {SSH_DB} -At -F"|" -c "{sql}"',
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    rows = []
    for line in out.stdout.strip().splitlines():
        parts = line.split('|')
        if len(parts) != 5:
            continue
        pid, name, is_company, n_cust, n_supp = parts
        rows.append({
            'id': int(pid),
            'name': name,
            'is_company': is_company == 't',
            'n_customer': int(n_cust or 0),
            'n_supplier': int(n_supp or 0),
        })
    return rows


def main():
    rows = fetch_rows()
    print(f"partners: {len(rows)}", file=sys.stderr)

    used_names = set()
    out = []
    for r in rows:
        key = f"sfa-{r['id']}"
        is_company = bool(r['is_company'])
        name = fake_name(key, is_company)
        # Guarantee unique names — a collision would merge two partners.
        n = 1
        while name in used_names:
            n += 1
            name = fake_name(key + str(n), is_company)
        used_names.add(name)

        street, num, zipc, city = fake_address(key)
        is_customer = r['n_customer'] > 0
        is_supplier = r['n_supplier'] > 0

        out.append({
            'id': r['id'],
            'name': name,
            'is_company': is_company,
            'street': f"{street} {num}",
            'zip': zipc,
            'city': city,
            'vat': fake_vat(key) if is_company else '',
            'orgnr': fake_orgnr(key) if is_company else '',
            'bankgiro': fake_bankgiro(key),
            'customer': is_customer,
            'supplier': is_supplier,
        })

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<odoo>\n')
        f.write('    <data noupdate="1">\n\n')
        f.write('        <!-- ================================================== -->\n')
        f.write('        <!-- Customers and suppliers                                    -->\n')
        f.write('        <!--                                                             -->\n')
        f.write('        <!-- Generated from the SFA production database and anonymised:  -->\n')
        f.write('        <!-- name, org number, VAT, address and bank giro are invented.  -->\n')
        f.write('        <!-- Structure (count, customer/supplier split, company vs       -->\n')
        f.write('        <!-- person) is preserved from the source.                       -->\n')
        f.write('        <!-- ================================================== -->\n\n')
        for p in out:
            f.write(f'        <record id="partner_{p["id"]}" model="res.partner">\n')
            f.write(f'            <field name="name">{xml_escape(p["name"])}</field>\n')
            f.write(f'            <field name="company_type">{"company" if p["is_company"] else "person"}</field>\n')
            f.write(f'            <field name="street">{xml_escape(p["street"])}</field>\n')
            f.write(f'            <field name="zip">{xml_escape(p["zip"])}</field>\n')
            f.write(f'            <field name="city">{xml_escape(p["city"])}</field>\n')
            f.write('            <field name="country_id" ref="base.se"/>\n')
            if p['is_company']:
                f.write(f'            <field name="vat">{p["vat"]}</field>\n')
                f.write(f'            <field name="company_registry">{p["orgnr"]}</field>\n')
            f.write(f'            <field name="ref">DEMO-{p["id"]}</field>\n')
            if p['customer']:
                f.write('            <field name="customer_rank">1</field>\n')
            if p['supplier']:
                f.write('            <field name="supplier_rank">1</field>\n')
            f.write('        </record>\n\n')
        f.write('    </data>\n</odoo>\n')

    print(f"wrote {OUT}", file=sys.stderr)
    print(f"customers: {sum(1 for p in out if p['customer'])}", file=sys.stderr)
    print(f"suppliers: {sum(1 for p in out if p['supplier'])}", file=sys.stderr)
    print(f"companies: {sum(1 for p in out if p['is_company'])}", file=sys.stderr)


if __name__ == '__main__':
    main()
