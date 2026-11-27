# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################
"""SIE 4-parser för Odoo 18.

Varför en egen parser: ``l10n_se_sie`` är skriven för Odoo 14/15 och
refererar till ``account.period`` / ``account.fiscalyear``, som Odoo 18 har
slopat (räkenskapsår styrs nu av ``res.company.fiscalyear_last_day/month``).
Dess ``import_sie()`` är dessutom avsiktligt blockerad med ``raise UserError``.

Den här parsern läser SIE 4 enligt SIE_filformat_ver_4B och skapar
``account.move`` direkt. Den hanterar:

  #KONTO   kontonr namn              -> skapa konto om det saknas
  #VER     serie nr datum [text] [regdatum]
  #TRANS   kontonr {objekt} belopp [transdat] [text] [kvantitet] [sign]
  #IB      år kontonr belopp         -> ingående balans
  #UB      år kontonr belopp         -> utgående balans (valideras)
  #RAR     år från till              -> räkenskapsår
  #FLAGGA, #PROGRAM, #FORMAT, #GEN, #SIETYP, #ORGNR, #FNAMN, #ADRESS,
  #ENHET, #KPTYP, #VALUTA, #DIM, #OBJEKT, #SRU, #PSALDO, #PBUDGET

Teckenkodning: SIE 4 är specificerad som CP437 (IBM PC 8-bit). Filer från
Fortnox är ofta UTF-8 eller Latin-1 i praktiken — vi provar i tur och ordning.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# SIE 4 anger CP437, men verkligheten är blandad
ENCODINGS = ('utf-8-sig', 'utf-8', 'cp437', 'latin-1')


def decode_sie(blob):
    """Avkoda SIE-fil. Returnerar (text, encoding)."""
    for enc in ENCODINGS:
        try:
            return blob.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return blob.decode('latin-1', errors='replace'), 'latin-1 (ersatt)'


def split_sie_line(line):
    """Dela en SIE-rad på blanksteg, med stöd för citerade fält.

    SIE använder citattecken runt strängar som innehåller blanksteg, och
    escapear ett citattecken genom att dubbla det ("").
    """
    tokens = []
    cur = []
    in_quote = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == '"':
            if in_quote and i + 1 < n and line[i + 1] == '"':
                cur.append('"')
                i += 2
                continue
            in_quote = not in_quote
            i += 1
            continue
        if ch in ' \t' and not in_quote:
            if cur:
                tokens.append(''.join(cur))
                cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if cur:
        tokens.append(''.join(cur))
    return tokens


def parse_amount(value):
    """SIE-belopp: punkt som decimaltecken, kan vara negativt."""
    if value is None or value == '':
        return 0.0
    try:
        return float(str(value).replace(',', '.'))
    except ValueError:
        return 0.0


class SieParser:
    """Tolkad SIE 4-fil."""

    def __init__(self, text):
        self.encoding = None
        self.sie_type = None
        self.company_name = None
        self.org_number = None
        self.accounts = {}        # kontonr -> {name, sru}
        self.vouchers = []        # [{series, number, date, text, regdate, lines}]
        self.opening = {}         # (year, account) -> amount
        self.closing = {}         # (year, account) -> amount
        self.fiscal_years = []    # [(year, from, to)]
        self.dimensions = {}      # dimnr -> name
        self.objects = {}         # (dim, code) -> name
        self.errors = []
        self._parse(text)

    def _parse(self, text):
        current = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line or not line.startswith('#'):
                continue
            tokens = split_sie_line(line)
            if not tokens:
                continue
            label = tokens[0].upper()

            try:
                if label == '#FLAGGA':
                    continue
                elif label == '#SIETYP':
                    self.sie_type = int(tokens[1])
                elif label == '#FNAMN':
                    self.company_name = tokens[1] if len(tokens) > 1 else ''
                elif label == '#ORGNR':
                    self.org_number = tokens[1] if len(tokens) > 1 else ''
                elif label == '#KONTO':
                    if len(tokens) >= 2:
                        self.accounts[tokens[1]] = {
                            'name': tokens[2] if len(tokens) > 2 else '',
                            'sru': [],
                        }
                elif label == '#SRU':
                    if len(tokens) >= 3 and tokens[1] in self.accounts:
                        self.accounts[tokens[1]]['sru'].append(tokens[2])
                elif label == '#RAR':
                    if len(tokens) >= 4:
                        self.fiscal_years.append((tokens[1], tokens[2], tokens[3]))
                elif label == '#DIM':
                    if len(tokens) >= 3:
                        self.dimensions[tokens[1]] = tokens[2]
                elif label == '#OBJEKT':
                    if len(tokens) >= 4:
                        self.objects[(tokens[1], tokens[2])] = tokens[3]
                elif label == '#VER':
                    current = {
                        'series': tokens[1] if len(tokens) > 1 else '',
                        'number': tokens[2] if len(tokens) > 2 else '',
                        'date': tokens[3] if len(tokens) > 3 else '',
                        'text': tokens[4] if len(tokens) > 4 else '',
                        'regdate': tokens[5] if len(tokens) > 5 else '',
                        'lines': [],
                    }
                    self.vouchers.append(current)
                elif label == '#TRANS':
                    if current is None:
                        self.errors.append('#TRANS utan föregående #VER')
                        continue
                    # #TRANS kontonr {objekt} belopp [transdat] [text] [kvant] [sign]
                    account = tokens[1] if len(tokens) > 1 else ''
                    idx = 2
                    objects = []

                    # Objektlistan är {dimnr "objektkod" dimnr "objektkod" ...}.
                    # Tokenizern delar vid blanksteg, så '{6' och 'P01}' kommer
                    # som separata tokens. Plocka ihop allt fram till '}'.
                    if idx < len(tokens) and tokens[idx].startswith('{'):
                        obj_tokens = []
                        first = tokens[idx]
                        if first == '{':
                            idx += 1
                        else:
                            obj_tokens.append(first[1:])
                            idx += 1
                        closed = first.endswith('}') and first != '{'
                        while idx < len(tokens) and not closed:
                            tok = tokens[idx]
                            if tok.endswith('}'):
                                obj_tokens.append(tok[:-1])
                                closed = True
                            else:
                                obj_tokens.append(tok)
                            idx += 1
                        # obj_tokens: [dimnr, objektkod, dimnr, objektkod, ...]
                        for k in range(0, len(obj_tokens) - 1, 2):
                            dim = obj_tokens[k]
                            obj = obj_tokens[k + 1]
                            if dim:
                                objects.append((dim, obj))

                    amount = parse_amount(tokens[idx]) if idx < len(tokens) else 0.0
                    idx += 1
                    trans_date = tokens[idx] if idx < len(tokens) else ''
                    idx += 1
                    trans_text = tokens[idx] if idx < len(tokens) else ''
                    idx += 1
                    quantity = tokens[idx] if idx < len(tokens) else ''
                    idx += 1
                    sign = tokens[idx] if idx < len(tokens) else ''

                    current['lines'].append({
                        'account': account,
                        'amount': amount,
                        'date': trans_date,
                        'text': trans_text,
                        'quantity': quantity,
                        'sign': sign,
                        'objects': objects,
                    })
                elif label == '#IB':
                    if len(tokens) >= 4:
                        self.opening[(tokens[1], tokens[2])] = parse_amount(tokens[3])
                elif label == '#UB':
                    if len(tokens) >= 4:
                        self.closing[(tokens[1], tokens[2])] = parse_amount(tokens[3])
            except (IndexError, ValueError) as e:
                self.errors.append('%s: %s' % (label, e))

    # ------------------------------------------------------------------
    # Validering
    # ------------------------------------------------------------------

    def validate(self):
        """Kontrollera balans per verifikation och IB/UB-konsistens."""
        problems = []

        for v in self.vouchers:
            total = sum(l['amount'] for l in v['lines'])
            if abs(total) > 0.005:
                problems.append(
                    'Verifikation %s/%s (%s) obalanserad: summa %.2f'
                    % (v['series'], v['number'], v['date'], total)
                )

        # IB + årets rörelser ska bli UB
        for (year, account), closing in self.closing.items():
            opening = self.opening.get((year, account), 0.0)
            movement = sum(
                l['amount']
                for v in self.vouchers
                for l in v['lines']
                if l['account'] == account
            )
            expected = opening + movement
            if abs(expected - closing) > 0.05:
                problems.append(
                    'Konto %s år %s: IB %.2f + rörelse %.2f = %.2f, men UB är %.2f'
                    % (account, year, opening, movement, expected, closing)
                )

        return problems

    def summary(self):
        return {
            'sie_type': self.sie_type,
            'company': self.company_name,
            'org_number': self.org_number,
            'accounts': len(self.accounts),
            'vouchers': len(self.vouchers),
            'transactions': sum(len(v['lines']) for v in self.vouchers),
            'fiscal_years': self.fiscal_years,
            'opening_balances': len(self.opening),
            'closing_balances': len(self.closing),
            'dimensions': len(self.dimensions),
            'objects': len(self.objects),
            'errors': self.errors,
        }
