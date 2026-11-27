#!/usr/bin/env python3
"""Generate quarterly accounting demo datasets from the SFA production database.

Reads the moves for each quarter, maps accounts to BAS codes (which both
SFA and the demo company's se_K2 chart use), maps partners to the
anonymised demo partners, and writes one JSON file per quarter.

The output is what l10n_se_account_demo loads through demo.dataset.
"""
import gzip
import json
import os
import subprocess
import sys
from collections import Counter

SSH_HOST = '192.168.11.145'
SSH_DB = 'odoo-sfa-ce-18-se-production'

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'data', 'datasets')

# 2023Q4 .. 2027Q4 — SFA accounting data starts 2023-10-31
QUARTERS = [(2023, 4)] + [
    (year, quarter)
    for year in (2024, 2025, 2026, 2027)
    for quarter in (1, 2, 3, 4)
]


def quarter_bounds(year, quarter):
    start_month = (quarter - 1) * 3 + 1
    start = f'{year}-{start_month:02d}-01'
    if quarter == 4:
        end = f'{year + 1}-01-01'
    else:
        end = f'{year}-{quarter * 3 + 1:02d}-01'
    return start, end


def run_sql(sql):
    """Run a query over ssh and return pipe-separated rows."""
    flat = ' '.join(sql.split())
    # Move line names contain '|' and would otherwise split the row in the
    # wrong place. '~|~' does not occur in the data and survives the shell.
    sep = '~|~' 
    cmd = [
        'ssh', '-o', 'ConnectTimeout=10', SSH_HOST,
        f'sudo -n -u postgres psql -d {SSH_DB} -At -F"{sep}" -c "{flat}"',
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def fetch_moves(start, end):
    sql = f"""
        SELECT am.id, am.name, am.date, am.move_type,
               COALESCE(aj.code, ''), COALESCE(am.partner_id, 0),
               COALESCE(am.invoice_date, am.date),
               COALESCE(am.invoice_date_due, am.date),
               regexp_replace(COALESCE(am.payment_reference, ''), E'[\n\r\t]+', ' ', 'g')
        FROM account_move am
        LEFT JOIN account_journal aj ON aj.id = am.journal_id
        WHERE am.state = 'posted'
          AND am.date >= '{start}' AND am.date < '{end}'
        ORDER BY am.id
    """
    rows = []
    for line in run_sql(sql):
        parts = line.split('~|~')
        if len(parts) != 9:
            continue
        rows.append({
            'id': int(parts[0]),
            'name': parts[1],
            'date': parts[2],
            'move_type': parts[3],
            'journal_code': parts[4],
            'partner_id': int(parts[5]),
            'invoice_date': parts[6],
            'invoice_date_due': parts[7],
            'payment_reference': parts[8],
        })
    return rows


def fetch_lines(move_ids):
    if not move_ids:
        return {}
    ids = ','.join(str(i) for i in move_ids)
    sql = f"""
        SELECT aml.move_id, COALESCE(aa.code_store->>'1', ''),
               COALESCE(aml.partner_id, 0), aml.debit, aml.credit,
               regexp_replace(COALESCE(aml.name, ''), E'[\\n\\r\\t]+', ' ', 'g'), COALESCE(aml.display_type, ''),
               COALESCE(aml.sequence, 0), COALESCE(aml.date_maturity, aml.date),
               COALESCE(at.name->>'en_US', '')
        FROM account_move_line aml
        LEFT JOIN account_account aa ON aa.id = aml.account_id
        LEFT JOIN account_tax at ON at.id = aml.tax_line_id
        WHERE aml.move_id IN ({ids})
        ORDER BY aml.move_id, aml.sequence, aml.id
    """
    result = {}
    for line in run_sql(sql):
        parts = line.split('~|~')
        if len(parts) != 10:
            continue
        mid = int(parts[0])
        result.setdefault(mid, []).append({
            'account_code': parts[1],
            'partner_id': int(parts[2]),
            'debit': float(parts[3] or 0),
            'credit': float(parts[4] or 0),
            'name': parts[5],
            'display_type': parts[6],
            'sequence': int(parts[7] or 0),
            'date_maturity': parts[8],
            'tax_name': parts[9],
        })
    return result


def fetch_partner_ids():
    """Partners with invoices in the demo period — the ones that were anonymised."""
    sql = """
        SELECT DISTINCT partner_id FROM account_move
        WHERE move_type IN ('out_invoice', 'in_invoice')
          AND partner_id IS NOT NULL
          AND date >= '2023-10-01' AND date < '2028-01-01'
    """
    return {int(r) for r in run_sql(sql) if r.isdigit()}


def synthesise_from(template_moves, year, quarter, seed):
    """Build a quarter from another quarter's shape.

    Used for 2027, which does not exist in the source. Same move types,
    journals, partners and account structure — dates shifted into the
    target quarter and amounts scaled slightly.
    """
    import hashlib
    import random

    rng = random.Random(seed)
    start, end = quarter_bounds(year, quarter)
    start_y, start_m = int(start[:4]), int(start[5:7])
    end_y, end_m = (int(end[:4]), int(end[5:7])) if end[5:7] != '01' else (int(end[:4]), 12)
    months = [(start_y, start_m), (start_y, start_m + 1), (start_y, start_m + 2)]

    out = []
    for i, m in enumerate(template_moves):
        src_month = int(m['date'][5:7])
        target_y, target_m = months[(src_month - 1) % 3]
        day = int(m['date'][8:10])
        # Clamp to the target month's length — 31 January must not become
        # 31 February.
        import calendar
        last = calendar.monthrange(target_y, target_m)[1]
        new_date = f'{target_y}-{target_m:02d}-{min(day, last):02d}'
        scale = 1.0 + rng.uniform(-0.12, 0.12)
        lines = []
        for ln in m['line_ids']:
            lines.append({
                **ln,
                'debit': round(ln['debit'] * scale, 2),
                'credit': round(ln['credit'] * scale, 2),
                'date_maturity': new_date,
            })
        # Sequence numbers must be unique inside a quarter. The template
        # quarter's numbers are reused, so each move gets a new index.
        prefix = m['name'].split('/')[0]
        new_name = f"{prefix}/{year}/{target_m:02d}/{i + 1:04d}"
        # Rounding the scaled amounts can leave a one-öre gap. Absorb it in
        # the largest line so every generated move balances exactly.
        debit = sum(ln['debit'] for ln in lines)
        credit = sum(ln['credit'] for ln in lines)
        gap = round(debit - credit, 2)
        if abs(gap) >= 0.01 and lines:
            biggest = max(lines, key=lambda ln: ln['debit'] + ln['credit'])
            if biggest['debit'] >= biggest['credit']:
                biggest['debit'] = round(biggest['debit'] - gap, 2)
            else:
                biggest['credit'] = round(biggest['credit'] + gap, 2)
        out.append({
            **m,
            'name': new_name,
            'date': new_date,
            'invoice_date': new_date,
            'invoice_date_due': new_date,
            'line_ids': lines,
        })
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    known_partners = fetch_partner_ids()
    print(f"kända demopartners: {len(known_partners)}", file=sys.stderr)

    total = 0
    for year, quarter in QUARTERS:
        start, end = quarter_bounds(year, quarter)
        moves = fetch_moves(start, end)
        if not moves:
            print(f"{year}Q{quarter}: inga moves", file=sys.stderr)
            continue
        lines = fetch_lines([m['id'] for m in moves])

        out = []
        for m in moves:
            partner = m['partner_id']
            # SFA has 'rounding' lines (öresutjämning). Odoo's
            # _compute_balance resets balance to 0 for them on invoices, so
            # the amount is folded into the payment_term line here instead
            # of being written as its own row.
            raw_lines = m['_lines'] if '_lines' in m else lines.get(m['id'], [])
            rounding = sum((ln['debit'] or 0) - (ln['credit'] or 0)
                           for ln in raw_lines
                           if ln.get('display_type') == 'rounding')
            kept = [ln for ln in raw_lines if ln.get('display_type') != 'rounding']
            if rounding and kept:
                target = next((ln for ln in kept
                               if ln.get('display_type') == 'payment_term'), None)
                if target is None:
                    target = max(kept, key=lambda ln: ln['debit'] + ln['credit'])
                if target['credit']:
                    target['credit'] = round(target['credit'] - rounding, 2)
                else:
                    target['debit'] = round(target['debit'] + rounding, 2)
            out.append({
                'name': m['name'],
                'date': m['date'],
                'move_type': m['move_type'],
                'journal_code': m['journal_code'],
                'partner_ref': f'DEMO-{partner}' if partner in known_partners else '',
                'invoice_date': m['invoice_date'],
                'invoice_date_due': m['invoice_date_due'],
                'payment_reference': m['payment_reference'],
                'line_ids': [
                    {
                        'account_code': ln['account_code'],
                        'partner_ref': (f"DEMO-{ln['partner_id']}"
                                        if ln['partner_id'] in known_partners
                                        else ''),
                        'debit': ln['debit'],
                        'credit': ln['credit'],
                        'name': ln['name'],
                        'display_type': ln['display_type'],
                        'sequence': ln['sequence'],
                        'date_maturity': ln['date_maturity'],
                        'tax_name': ln['tax_name'],
                    }
                    for ln in kept
                ],
            })

        path = os.path.join(OUT_DIR, f'{year}q{quarter}.json.gz')
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        size = os.path.getsize(path) / 1024
        total += len(out)
        print(f"{year}Q{quarter}: {len(out)} moves, {size:.0f} kB",
              file=sys.stderr)

    # 2027 does not exist in the source. Build it from 2026's shape so the
    # future quarters have the same structure as the historic ones.
    template = None
    for year, quarter in [(2026, 1), (2025, 1), (2024, 1)]:
        path = os.path.join(OUT_DIR, f'{year}q{quarter}.json.gz')
        if os.path.exists(path):
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                template = json.load(f)
            print(f"2027 mall: {year}Q{quarter} ({len(template)} moves)",
                  file=sys.stderr)
            break
    if template:
        for quarter in (1, 2, 3, 4):
            out = synthesise_from(template, 2027, quarter, seed=2027 * 10 + quarter)
            path = os.path.join(OUT_DIR, f'2027q{quarter}.json.gz')
            with gzip.open(path, 'wt', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
            total += len(out)
            print(f"2027Q{quarter}: {len(out)} moves (syntetisk)",
                  file=sys.stderr)

    print(f"totalt {total} moves", file=sys.stderr)


if __name__ == '__main__':
    main()
