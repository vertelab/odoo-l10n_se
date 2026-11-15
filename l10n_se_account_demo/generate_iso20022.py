#!/usr/bin/env python3
"""Generate the ISO 20022 files for the demo quarters that carry them.

Two kinds of file, one per month, for 2026Q2..2026Q4:

    data/files/pain001/2026-04.xml … 2026-12.xml
    data/files/camt053/2026-04.xml … 2026-12.xml

pain.001 is the payment order the company sends to the bank: one
transaction per vendor payment (account 2440) in the month. camt.053 is
the statement the bank sends back: one entry per bank transaction in the
month, with one transaction detail per invoice it settles — so a bank
giro payment covering several invoices can be matched invoice by invoice.

Both are built from the same quarterly dataset the loader reads, so the
files describe exactly the payments that are in the books. The wizard
loads them as files; nothing is generated at load time.

Usage:  python3 generate_iso20022.py [--check]
        --check validates the existing files without rewriting them.
"""
import argparse
import gzip
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, 'data', 'datasets')
FILE_DIR = os.path.join(HERE, 'data', 'files')
PAIN_DIR = os.path.join(FILE_DIR, 'pain001')
CAMT_DIR = os.path.join(FILE_DIR, 'camt053')
# pain.001.001.09 is the schema l10n_se_credit_transfer already ships.
# camt.053.001.02 is the official ISO 20022 schema, kept here because no
# other module in the repository carries it.
PAIN_XSD = os.path.join(os.path.dirname(HERE), 'l10n_se_credit_transfer',
                        'data', 'pain.001.001.09.xsd')
CAMT_XSD = os.path.join(HERE, 'data', 'xsd', 'camt.053.001.02.xsd')

# Quarters that carry ISO 20022 files (design D5/D6). 2023Q4..2026Q1 are
# reconciled without files, 2027 is future and has none either.
FILE_QUARTERS = [(2026, 2), (2026, 3), (2026, 4)]

PAIN_NS = 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09'
CAMT_NS = 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'

# The demo company and its bank. Fictional, like the rest of the demo.
COMPANY_NAME = 'Aronssons Montage AB'
COMPANY_ORGNR = '556060-0000'
COMPANY_BANKGIRO = '5051-2345'
COMPANY_IBAN = 'SE4550000000051012345678'
COMPANY_BIC = 'ESSESESS'
# The bank's own reference prefix in camt.053. Stable across runs so an
# imported statement is recognisable.
ACCT_SVCR_PREFIX = '50512345'

# BAS accounts that identify the two kinds of payment in the dataset.
RECEIVABLE = '1510'
PAYABLE = '2440'
# Bank accounts inside the company's own books. A bank statement line
# moves money between these and the outside world.
BANK_ACCOUNTS = {'1930', '1933'}


def month_bounds(year, month):
    if month == 12:
        return f'{year}-12-01', f'{year + 1}-01-01'
    return f'{year}-{month:02d}-01', f'{year}-{month + 1:02d}-01'


def load_quarter(year, quarter):
    path = os.path.join(DATA_DIR, f'{year}q{quarter}.json.gz')
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def move_amount(move):
    """The amount of a payment move — the receivable/payable side."""
    for line in move['line_ids']:
        if line['account_code'] == RECEIVABLE and line['credit']:
            return round(line['credit'], 2)
        if line['account_code'] == PAYABLE and line['debit']:
            return round(line['debit'], 2)
    return 0.0


def invoice_items(move):
    """The invoices a payment move settles, one item per invoice.

    The dataset carries them as receivable/payable lines. On a customer
    payment the settled invoice is the credit line; the debit line is the
    opening balance the payment is matched against and is not an invoice.
    On a vendor payment there is a single payable line.
    """
    items = []
    for line in move['line_ids']:
        if line['account_code'] == RECEIVABLE and line['credit']:
            items.append({
                'amount': round(line['credit'], 2),
                'reference': (line['name'] or '').strip(),
            })
        elif line['account_code'] == PAYABLE and line['debit']:
            items.append({
                'amount': round(line['debit'], 2),
                'reference': (line['name'] or '').strip(),
            })
    return items


def payment_reference(move, items):
    """The reference a bank puts on the statement line.

    The invoice's OCR number when the payment settles exactly one invoice
    and the dataset carries an OCR number. Otherwise the invoice numbers,
    which is what the bank giro shows for a batch payment.
    """
    if len(items) == 1 and items[0]['reference'].isdigit():
        return items[0]['reference']
    # Max35Text in camt.053: a long batch of invoice numbers is cut, the
    # details below still carry each reference in full.
    return ' '.join(i['reference'] for i in items if i['reference'])[:35]


def is_customer_payment(move):
    return any(ln['account_code'] == RECEIVABLE and ln['credit']
               for ln in move['line_ids'])


def is_vendor_payment(move):
    return any(ln['account_code'] == PAYABLE and ln['debit']
               for ln in move['line_ids'])


def is_bank_move(move):
    """A move on a bank account that moves money to or from the outside."""
    return (move['journal_code'] == 'BNK1'
            and any(ln['account_code'] in BANK_ACCOUNTS
                    for ln in move['line_ids']))


def month_moves(moves, year, month):
    start, end = month_bounds(year, month)
    return [m for m in moves if start <= m['date'] < end]


# ----------------------------------------------------------------------
# pain.001 — payment order
# ----------------------------------------------------------------------

def el(parent, tag, text=None, **attrib):
    node = etree.SubElement(parent, tag, attrib)
    if text is not None:
        node.text = text
    return node


def build_pain(year, month, moves):
    """Build one pain.001.001.09 document for the month's vendor payments."""
    payments = [m for m in moves
                if m['journal_code'] == 'BNK1' and is_vendor_payment(m)]
    if not payments:
        return None

    root = etree.Element('Document', nsmap={None: PAIN_NS})
    initn = el(root, 'CstmrCdtTrfInitn')

    total = round(sum(move_amount(m) for m in payments), 2)
    msg_id = f'DEMO-PAIN-{year}{month:02d}'
    gh = el(initn, 'GrpHdr')
    el(gh, 'MsgId', msg_id)
    el(gh, 'CreDtTm', f'{year}-{month:02d}-01T06:00:00')
    el(gh, 'NbOfTxs', str(len(payments)))
    el(gh, 'CtrlSum', f'{total:.2f}')
    party = el(gh, 'InitgPty')
    el(party, 'Nm', COMPANY_NAME)
    party_id = el(party, 'Id')
    org_id = el(party_id, 'OrgId')
    other = el(org_id, 'Othr')
    el(other, 'Id', COMPANY_ORGNR.replace('-', ''))
    el(el(other, 'SchmeNm'), 'Cd', 'CUST')

    # One PmtInf per execution date, the way the payment order batches.
    by_date = OrderedDict()
    for move in sorted(payments, key=lambda m: (m['date'], m['name'])):
        by_date.setdefault(move['date'], []).append(move)

    for index, (exec_date, day_moves) in enumerate(by_date.items(), 1):
        day_total = round(sum(move_amount(m) for m in day_moves), 2)
        pmt = el(initn, 'PmtInf')
        el(pmt, 'PmtInfId', f'{msg_id}-{index:02d}')
        el(pmt, 'PmtMtd', 'TRF')
        el(pmt, 'NbOfTxs', str(len(day_moves)))
        el(pmt, 'CtrlSum', f'{day_total:.2f}')
        tp = el(pmt, 'PmtTpInf')
        el(el(tp, 'SvcLvl'), 'Cd', 'NURG')
        el(el(pmt, 'ReqdExctnDt'), 'Dt', exec_date)

        debtor = el(pmt, 'Dbtr')
        el(debtor, 'Nm', COMPANY_NAME)
        dbtr_acct = el(pmt, 'DbtrAcct')
        acct_id = el(dbtr_acct, 'Id')
        acct_other = el(acct_id, 'Othr')
        el(acct_other, 'Id', COMPANY_BANKGIRO.replace('-', ''))
        el(el(acct_other, 'SchmeNm'), 'Prtry', 'BGNR')
        dbtr_agent = el(pmt, 'DbtrAgt')
        el(el(dbtr_agent, 'FinInstnId'), 'BICFI', COMPANY_BIC)
        el(pmt, 'ChrgBr', 'SLEV')

        for position, move in enumerate(day_moves, 1):
            amount = move_amount(move)
            tx = el(pmt, 'CdtTrfTxInf')
            pmt_id = el(tx, 'PmtId')
            el(pmt_id, 'InstrId', f'{move["name"]}-{position:02d}')
            # EndToEndId carries the OCR number of the invoice being paid —
            # the same value the statement line comes back with.
            el(pmt_id, 'EndToEndId', move['payment_reference'] or 'NOTPROVIDED')
            amt = el(tx, 'Amt')
            el(amt, 'InstdAmt', f'{amount:.2f}', Ccy='SEK')

            creditor = el(tx, 'Cdtr')
            el(creditor, 'Nm', move['partner_name'])
            postal = el(creditor, 'PstlAdr')
            if move.get('street'):
                el(postal, 'StrtNm', move['street'])
            if move.get('zip'):
                el(postal, 'PstCd', move['zip'])
            if move.get('city'):
                el(postal, 'TwnNm', move['city'])
            el(postal, 'Ctry', 'SE')

            cdtr_acct = el(tx, 'CdtrAcct')
            cdtr_id = el(cdtr_acct, 'Id')
            cdtr_other = el(cdtr_id, 'Othr')
            el(cdtr_other, 'Id', move['partner_bankgiro'])
            el(el(cdtr_other, 'SchmeNm'), 'Prtry', 'BGNR')

            if move['payment_reference']:
                rmt = el(tx, 'RmtInf')
                el(rmt, 'Ustrd', f'OCR {move["payment_reference"]}')
    return root


# ----------------------------------------------------------------------
# camt.053 — bank statement
# ----------------------------------------------------------------------

def build_camt(year, month, moves, opening_balance):
    """Build one camt.053.001.02 statement for the month.

    One Ntry per bank transaction, one TxDtls per invoice it settles.
    """
    entries = [m for m in moves if is_bank_move(m)]
    if not entries:
        return None

    root = etree.Element('Document', nsmap={None: CAMT_NS})
    statement = el(root, 'BkToCstmrStmt')
    grp = el(statement, 'GrpHdr')
    stmt_id = f'DEMO-CAMT-{year}{month:02d}'
    el(grp, 'MsgId', stmt_id)
    el(grp, 'CreDtTm', f'{year}-{month:02d}-28T23:59:59')
    el(grp, 'AddtlInf', f'Kontoutdrag {COMPANY_BANKGIRO}')

    stmt = el(statement, 'Stmt')
    el(stmt, 'Id', stmt_id)
    el(stmt, 'CreDtTm', f'{year}-{month:02d}-28T23:59:59')

    account = el(stmt, 'Acct')
    acct_id = el(account, 'Id')
    acct_other = el(acct_id, 'Othr')
    el(acct_other, 'Id', COMPANY_BANKGIRO.replace('-', ''))
    el(el(acct_other, 'SchmeNm'), 'Prtry', 'BGNR')
    el(account, 'Ccy', 'SEK')
    owner = el(account, 'Ownr')
    el(owner, 'Nm', COMPANY_NAME)
    owner_id = el(owner, 'Id')
    owner_org = el(owner_id, 'OrgId')
    owner_other = el(owner_org, 'Othr')
    el(owner_other, 'Id', COMPANY_ORGNR.replace('-', ''))
    el(el(owner_other, 'SchmeNm'), 'Cd', 'CUST')
    el(account, 'Svcr')
    servicer = account.find('Svcr')
    fin = el(servicer, 'FinInstnId')
    # camt.053.001.02 still calls the BIC element BIC; BICFI is the name
    # from .08 onwards.
    el(fin, 'BIC', COMPANY_BIC)

    # The schema puts every Bal before the first Ntry, so the closing
    # balance has to be known before the entries are written.
    ordered = sorted(entries, key=lambda m: (m['date'], m['name']))
    balance = opening_balance
    for move in ordered:
        amount = move_amount(move)
        balance = round(balance + (amount if is_customer_payment(move)
                                   else -amount), 2)

    opening = el(stmt, 'Bal')
    opening_type = el(opening, 'Tp')
    el(el(opening_type, 'CdOrPrtry'), 'Cd', 'OPBD')
    el(opening, 'Amt', f'{opening_balance:.2f}', Ccy='SEK')
    el(opening, 'CdtDbtInd', 'CRDT' if opening_balance >= 0 else 'DBIT')
    opening_date = el(opening, 'Dt')
    el(opening_date, 'Dt', month_bounds(year, month)[0])

    closing = el(stmt, 'Bal')
    closing_type = el(closing, 'Tp')
    el(el(closing_type, 'CdOrPrtry'), 'Cd', 'CLBD')
    el(closing, 'Amt', f'{balance:.2f}', Ccy='SEK')
    el(closing, 'CdtDbtInd', 'CRDT' if balance >= 0 else 'DBIT')
    closing_date = el(closing, 'Dt')
    el(closing_date, 'Dt', month_bounds(year, month)[1])

    for position, move in enumerate(ordered, 1):
        amount = move_amount(move)
        credit = is_customer_payment(move)
        balance = round(balance + (amount if credit else -amount), 2)

        entry = el(stmt, 'Ntry')
        el(entry, 'NtryRef', f'{ACCT_SVCR_PREFIX}{year}{month:02d}{position:04d}')
        el(entry, 'Amt', f'{amount:.2f}', Ccy='SEK')
        el(entry, 'CdtDbtInd', 'CRDT' if credit else 'DBIT')
        el(entry, 'Sts', 'BOOK')
        book = el(entry, 'BookgDt')
        el(book, 'Dt', move['date'])
        value = el(entry, 'ValDt')
        el(value, 'Dt', move['date'])
        el(entry, 'AcctSvcrRef',
           f'{ACCT_SVCR_PREFIX}{year}{month:02d}{position:04d}')
        bank_tx = el(entry, 'BkTxCd')
        domain = el(bank_tx, 'Domn')
        el(domain, 'Cd', 'PMNT')
        family = el(domain, 'Fmly')
        el(family, 'Cd', 'RCDT' if credit else 'ICDT')
        el(family, 'SubFmlyCd', 'ESCT')

        details = el(entry, 'NtryDtls')
        for item in invoice_items(move):
            tx = el(details, 'TxDtls')
            refs = el(tx, 'Refs')
            # AcctSvcrRef comes before EndToEndId in TransactionReferences2.
            el(refs, 'AcctSvcrRef',
               f'{ACCT_SVCR_PREFIX}{year}{month:02d}{position:04d}')
            if item['reference']:
                # The OCR number (or the invoice number) the payment was
                # made against — this is what reconciliation matches on.
                el(refs, 'EndToEndId', item['reference'][:35])
            # The transaction amount lives in AmtDtls/TxAmt in camt.053.
            # The OCA parser reads it from there when TxDtls carries no
            # bare Amt.
            amt_dtls = el(tx, 'AmtDtls')
            tx_amount = el(amt_dtls, 'TxAmt')
            el(tx_amount, 'Amt', f'{item["amount"]:.2f}', Ccy='SEK')
            # EntryTransaction2 has no CdtDbtInd — the sign comes from the
            # entry the detail belongs to.
            parties = el(tx, 'RltdPties')
            if credit:
                debtor = el(parties, 'Dbtr')
                el(debtor, 'Nm', move['partner_name'])
            else:
                creditor = el(parties, 'Cdtr')
                el(creditor, 'Nm', move['partner_name'])
            if item['reference']:
                rmt = el(tx, 'RmtInf')
                el(rmt, 'Ustrd', f'OCR {item["reference"]}'[:140])
        reference = payment_reference(move, invoice_items(move))
        if reference:
            el(entry, 'AddtlNtryInf', reference)
    return root


# ----------------------------------------------------------------------
# Partner data and the opening balance
# ----------------------------------------------------------------------

def load_partners():
    """The demo partners, keyed by their DEMO-<id> ref."""
    path = os.path.join(os.path.dirname(HERE), 'l10n_se_demo_company',
                        'data', 'partners.xml')
    tree = etree.parse(path)
    partners = {}
    for record in tree.getroot().iter('record'):
        ref = record.find("field[@name='ref']")
        if ref is None or not (ref.text or '').startswith('DEMO-'):
            continue
        partners[ref.text] = {
            'name': record.find("field[@name='name']").text,
            'street': (record.find("field[@name='street']").text
                       if record.find("field[@name='street']") is not None
                       else ''),
            'zip': (record.find("field[@name='zip']").text
                    if record.find("field[@name='zip']") is not None else ''),
            'city': (record.find("field[@name='city']").text
                     if record.find("field[@name='city']") is not None
                     else ''),
        }
    return partners


def opening_balance(year, month):
    """The bank balance at the start of the month.

    The dataset has no opening balance of its own. The statement is
    anchored at zero for the first month of the first file quarter and
    then carried forward, so the closing balance of one month is the
    opening balance of the next. The value is an artefact of the demo and
    documented as such — it is not taken from the source.
    """
    balance = 0.0
    for quarter_year, quarter in FILE_QUARTERS:
        for quarter_month in range((quarter - 1) * 3 + 1, quarter * 3 + 1):
            if (quarter_year, quarter_month) >= (year, month):
                return balance
            start, end = month_bounds(quarter_year, quarter_month)
            moves = [m for m in load_quarter(quarter_year, quarter)
                     if start <= m['date'] < end]
            for move in moves:
                if not is_bank_move(move):
                    continue
                amount = move_amount(move)
                balance += amount if is_customer_payment(move) else -amount
            balance = round(balance, 2)
    return balance


def enrich(moves, partners):
    """Attach the partner name and bank giro the files need."""
    out = []
    for move in moves:
        partner = partners.get(move.get('partner_ref') or '')
        if not partner:
            # Payments without a partner ref (rare) cannot be paid to a
            # named creditor; the file uses the bank's own text instead.
            partner = {'name': 'Okänd mottagare', 'street': '', 'zip': '',
                       'city': ''}
        out.append({
            **move,
            'partner_name': partner['name'],
            'street': partner.get('street', ''),
            'zip': partner.get('zip', ''),
            'city': partner.get('city', ''),
            # The partner file has no bank account records, so the bank
            # giro is derived from the partner ref. Stable across runs.
            'partner_bankgiro': fake_bankgiro(move.get('partner_ref') or ''),
        })
    return out


def fake_bankgiro(key):
    """A bank giro number derived from the partner ref.

    The demo partners have no res.partner.bank records, so the payment
    files need an account number of their own. Deterministic, so two runs
    give the same file.
    """
    digits = ''.join(str((sum(ord(c) for c in key) + i * 7) % 10)
                     for i in range(8))
    return f'{digits[:4]}-{digits[4:]}'


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def validate(path, xsd_path):
    schema = etree.XMLSchema(etree.parse(xsd_path))
    document = etree.parse(path)
    schema.assertValid(document)
    return True


def check_pain_coverage(path, moves):
    """Every vendor payment in the month must be a transaction in the file."""
    tree = etree.parse(path)
    ns = {'p': PAIN_NS}
    transactions = tree.findall('.//p:CdtTrfTxInf', ns)
    payments = [m for m in moves
                if m['journal_code'] == 'BNK1' and is_vendor_payment(m)]
    assert len(transactions) == len(payments), (
        f'{path}: {len(transactions)} transactions, {len(payments)} payments')
    total = round(sum(float(t.find('p:Amt/p:InstdAmt', ns).text)
                      for t in transactions), 2)
    expected = round(sum(move_amount(m) for m in payments), 2)
    assert total == expected, f'{path}: control sum {total} != {expected}'
    return len(transactions)


def check_camt_coverage(path, moves):
    """One entry per bank transaction, one detail per invoice."""
    tree = etree.parse(path)
    ns = {'c': CAMT_NS}
    entries = tree.findall('.//c:Ntry', ns)
    bank_moves = [m for m in moves if is_bank_move(m)]
    assert len(entries) == len(bank_moves), (
        f'{path}: {len(entries)} entries, {len(bank_moves)} bank moves')
    multi = 0
    for entry in entries:
        details = entry.findall('c:NtryDtls/c:TxDtls', ns)
        assert details, f'{path}: entry without transaction details'
        entry_amount = round(float(entry.find('c:Amt', ns).text), 2)
        detail_sum = round(sum(float(d.find('c:AmtDtls/c:TxAmt/c:Amt', ns).text)
                               for d in details), 2)
        assert entry_amount == detail_sum, (
            f'{path}: entry {entry_amount} != details {detail_sum}')
        if len(details) > 1:
            multi += 1
    return len(entries), multi


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true',
                        help='validate existing files instead of writing')
    args = parser.parse_args()

    partners = load_partners()
    if not args.check:
        os.makedirs(PAIN_DIR, exist_ok=True)
        os.makedirs(CAMT_DIR, exist_ok=True)

    total_pain = total_camt = total_multi = 0
    for year, quarter in FILE_QUARTERS:
        moves = load_quarter(year, quarter)
        for month in range((quarter - 1) * 3 + 1, quarter * 3 + 1):
            month_moves_ = enrich(month_moves(moves, year, month), partners)
            pain_path = os.path.join(PAIN_DIR, f'{year}-{month:02d}.xml')
            camt_path = os.path.join(CAMT_DIR, f'{year}-{month:02d}.xml')

            if not args.check:
                pain = build_pain(year, month, month_moves_)
                if pain is not None:
                    etree.ElementTree(pain).write(
                        pain_path, pretty_print=True, xml_declaration=True,
                        encoding='UTF-8')
                camt = build_camt(year, month, month_moves_,
                                  opening_balance(year, month))
                if camt is not None:
                    etree.ElementTree(camt).write(
                        camt_path, pretty_print=True, xml_declaration=True,
                        encoding='UTF-8')

            validate(pain_path, PAIN_XSD)
            transactions = check_pain_coverage(pain_path, month_moves_)
            validate(camt_path, CAMT_XSD)
            entries, multi = check_camt_coverage(camt_path, month_moves_)
            total_pain += transactions
            total_camt += entries
            total_multi += multi
            print(f'{year}-{month:02d}: pain.001 {transactions} txs, '
                  f'camt.053 {entries} entries ({multi} with several '
                  f'invoices)', file=sys.stderr)

    print(f'totalt {total_pain} betalningar, {total_camt} bankhändelser, '
          f'{total_multi} händelser med flera fakturor', file=sys.stderr)


if __name__ == '__main__':
    main()
