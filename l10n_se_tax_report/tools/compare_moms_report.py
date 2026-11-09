# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Verify the report engine against two independent references, and time it.

Run from the Odoo shell:

    sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d <db> --no-http \\
        < compare_moms_report.py

or interactively:

    >>> from odoo.addons.l10n_se_tax_report.tools.compare_moms_report import run
    >>> run(env, '2026-01-01', '2026-12-31')

Why two references and not one
------------------------------
The Swedish VAT boxes are computed in three ways:

* **MIS Builder** selects on the *tax name* (``('tax_line_id.name','=','MP1')``)
  or on account codes (``bal[3000,…]``).
* **The new report** (``account.report`` generated from MIS) keeps the tax-name
  selection, or uses tags.
* **Core** (``l10n_se``'s ``skatterapport``) selects on *tax tags* only
  (``+se_10``).

One reference cannot tell "the new engine is wrong" from "the reference is
wrong". Two can: when two agree and one differs, the odd one out is the
suspect. That is the whole point of the third column.

Interactive, not batch
----------------------
``account.report`` caches nothing. Every call to ``_get_lines()`` hits
``account.move.line`` afresh — it is what happens when a user changes the date
picker. So the number that matters is **how long a user waits after changing
the date**, not how long a batch of reports takes.

Time is therefore measured as *one* ``_get_lines()`` call per sample,
repeated, with the unfold mode stated explicitly: a collapsed balance sheet
(101 rows, few visible) is not the same work as a fully expanded one.
"""

import logging
import time

_logger = logging.getLogger(__name__)

# MIS KPI name -> report line code. Verified against
# ``l10n_se_mis/data/mis_momsdeklaration_report.xml``: the set of names here
# equals the set of KPI records there (28 == 28).
BOX_BY_KPI = {
    'ForsMomsEjAnnan': 'se_05',
    # Box 06 is named 'Momspliktiga' in the shipped data file and
    # 'UttagMoms' in older customer databases (SFA runs one of those).
    # Same box, two names -- accept both rather than miss the row.
    'Momspliktiga': 'se_06',
    'UttagMoms': 'se_06',
    'UlagMargbesk': 'se_07',
    'HyrinkomstFriv': 'se_08',
    'MomsUtgHog': 'se_10',
    'MomsUtgMedel': 'se_11',
    'MomsUtgLag': 'se_12',
    'InkopVaruAnnatEg': 'se_20',
    'InkopTjanstAnnatEg': 'se_21',
    'InkopTjanstUtomEg': 'se_22',
    'InkopVaruSverige': 'se_23',
    'InkopTjanstSverige': 'se_24',
    'MomsInkopUtgHog': 'se_30',
    'MomsInkopUtgMedel': 'se_31',
    'MomsInkopUtgLag': 'se_32',
    'ForsVaruAnnatEg': 'se_35',
    'ForsVaruUtomEg': 'se_36',
    'InkopVaruMellan3p': 'se_37',
    'ForsVaruMellan3p': 'se_38',
    'ForsTjSkskAnnatEg': 'se_39',
    'ForsTjOvrUtomEg': 'se_40',
    'ForsKopareSkskSverige': 'se_41',
    'ForsOvrigt': 'se_42',
    'MomsIngAvdr': 'se_48',
    'MomsUlagImport': 'se_50',
    'MomsImportUtgHog': 'se_60',
    'MomsImportUtgMedel': 'se_61',
    'MomsImportUtgLag': 'se_62',
}

# Tolerance: large enough that rounding never raises a false alarm, small
# enough that a one-krona error always shows. Stated in the output.
DEFAULT_TOLERANCE = 0.5

# Classification of a difference. Never leave one unexplained.
FEL_NY = 'fel i nya motorn'
FEL_REFERENS = 'fel i referensen'
SEMANTIK = 'förväntad semantikskillnad'
OKLAR = 'oklar'


class Timeout(Exception):
    """Raised when --limit-seconds is exceeded."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _count_posted_lines(env, date_from, date_to, company):
    """How much data the period actually contains."""
    return env['account.move.line'].search_count([
        ('company_id', '=', company.id),
        ('parent_state', '=', 'posted'),
        ('date', '>=', date_from),
        ('date', '<=', date_to),
    ])


def _mis_amounts(env, date_from, date_to, company):
    """Per-KPI amounts from the old MIS declaration report."""
    mis_report = env.ref('l10n_se_mis.report_md', raise_if_not_found=False)
    if not mis_report:
        return {}, 'l10n_se_mis.report_md not found'

    instance = env['mis.report.instance'].search([
        ('report_id', '=', mis_report.id),
        ('company_id', '=', company.id),
    ], limit=1)
    if not instance:
        instance = env['mis.report.instance'].create({
            'name': 'compare-tmp',
            'report_id': mis_report.id,
            'company_id': company.id,
            'period_ids': [(0, 0, {
                'name': 'compare', 'sequence': 1, 'mode': 'fix',
                'manual_date_from': date_from, 'manual_date_to': date_to,
            })],
        })
    else:
        for period in instance.period_ids:
            period.write({
                'manual_date_from': date_from,
                'manual_date_to': date_to,
            })

    amounts = {}
    for row in instance._compute_matrix().iter_rows():
        cells = list(row.iter_cells())
        if not cells or not isinstance(cells[0].val, (int, float)):
            continue
        # auto_expand_accounts puts the row total first; later cells are
        # account detail and must NOT be added on top.
        amounts[row.kpi.name] = float(cells[0].val)
    return amounts, None


def _source_report(env):
    """The core Swedish tax report (``skatterapport``)."""
    return env['account.report'].search([
        ('country_id.code', '=', 'SE'),
        ('name', 'in', ('skatterapport', 'Tax Report')),
    ], limit=1)


def _generated_report(env, kind='md'):
    """A report generated from MIS by the bridge's data files."""
    names = {
        'md': ['Momsdeklaration'],
        'br': ['Balansräkning'],
        'rr': ['Resultaträkning'],
    }.get(kind, [])
    if not names:
        return env['account.report']
    return env['account.report'].search([('name', 'in', names)], limit=1)


def _lines_to_amounts(report, options):
    """{code: amount} from one _get_lines() call."""
    lines = report._get_lines(options)
    amounts = {}
    for line in lines:
        code = line.get('code')
        if not code:
            continue
        columns = line.get('columns') or []
        if columns:
            amounts[code] = float(columns[0].get('no_format') or 0.0)
    return amounts


def _options(env, date_from, date_to, unfold):
    return {
        'date': {'date_from': date_from, 'date_to': date_to},
        'company_ids': [env.company.id],
        'unfold_all': unfold,
    }


# ----------------------------------------------------------------------
# Classification (2.2)
# ----------------------------------------------------------------------
def classify(row, ctx):
    """Explain one difference instead of leaving it as a bare number.

    ``ctx`` carries what the classifier needs: whether the period contains a
    credit note, and whether core can see the tax at all.
    """
    mis, new, core, diff = row['mis'], row['new'], row['core'], row['diff']

    # A credit note reverses the sign of its tax line. MIS's `crd` expands to
    # ('credit', '<>', 0), so the debit side of a credit note is invisible to
    # it: MIS ignores the note, the new report nets it.
    if ctx.get('has_credit_note') and abs(abs(diff) - ctx['credit_note_amount']) < 0.5:
        return FEL_REFERENS, (
            "kreditnota på %.2f syns inte för MIS (crd filtrerar på credit<>0); "
            "den nya rapporten nettoredovisar" % ctx['credit_note_amount'])

    # A 0 % marker tax produces no tax line, so a tax_line_id selection finds
    # nothing. Core selects on tags and may see it, or not, depending on chart.
    if core is not None and core == 0 and (mis or new):
        return SEMANTIK, (
            "core väljer på taggar; skatten saknar tagg i den här kontoplanen")

    # Two agree, one differs -> the odd one out is the suspect.
    if abs(mis - new) < 0.5 and abs(core - mis) >= 0.5:
        return SEMANTIK, "MIS och nya rapporten stämmer; core avviker"
    if abs(mis - core) < 0.5 and abs(new - mis) >= 0.5:
        return FEL_NY, "MIS och core stämmer; den nya rapporten avviker"

    return OKLAR, "kunde inte klassas automatiskt"


def _credit_note_context(env, date_from, date_to, company):
    """Does the period contain a credit note, and how much tax does it carry?"""
    notes = env['account.move.line'].search([
        ('company_id', '=', company.id),
        ('parent_state', '=', 'posted'),
        ('date', '>=', date_from),
        ('date', '<=', date_to),
        ('move_id.move_type', 'in', ('out_refund', 'in_refund')),
        ('tax_line_id', '!=', False),
    ])
    total = sum(abs(l.balance) for l in notes)
    return {'has_credit_note': bool(notes), 'credit_note_amount': total}


# ----------------------------------------------------------------------
# Correctness (2.1, 2.3)
# ----------------------------------------------------------------------
def compare(env, date_from, date_to, company=None, tol=DEFAULT_TOLERANCE):
    """Three-way per-box comparison. Returns a list of row dicts."""
    company = company or env.company
    unfiltered = _count_posted_lines(env, date_from, date_to, company)

    print("=" * 92)
    print("MOMSDEKLARATION — trevägsjämförelse")
    print("Företag: %s   Period: %s .. %s" % (company.name, date_from, date_to))
    print("Tolerans: %.2f kr   Bokförda rader i perioden: %d"
          % (tol, unfiltered))
    print("=" * 92)

    if unfiltered == 0:
        print("")
        print("VARNING: perioden innehåller inga bokförda rader.")
        print("En tom mätning bevisar ingenting — välj en period med data.")
        return []

    mis, mis_error = _mis_amounts(env, date_from, date_to, company)
    if mis_error:
        print("MIS: %s" % mis_error)

    core_report = _source_report(env)
    if not core_report:
        print("Core: ingen skatterapport hittad")
        core = {}
    else:
        core = _lines_to_amounts(core_report, _options(env, date_from, date_to, True))

    generated = _generated_report(env, 'md')
    if not generated:
        print("Ny rapport: ingen 'Momsdeklaration' hittad")
        new = {}
    else:
        new = _lines_to_amounts(generated, _options(env, date_from, date_to, True))

    ctx = _credit_note_context(env, date_from, date_to, company)

    # An engine that returns 0 for every box is not "a company without VAT" --
    # it is an engine that is not computing. Reporting "0 differ" on that is
    # the exact false comfort this tool exists to prevent.
    for label, amounts, error in (
            ('MIS', mis, mis_error),
            ('Ny rapport', new, None if generated else 'rapporten hittades inte'),
            ('Core', core, None if core_report else 'rapporten hittades inte')):
        if error:
            print("VARNING: %s kan inte mätas: %s" % (label, error))
            continue
        if amounts and not any(abs(v) > 0.01 for v in amounts.values()):
            print("VARNING: %s gav 0 på ALLA rutor — motorn räknar inte. "
                  "En sådan kolumn bevisar ingenting." % label)

    print("%-5s %-24s %13s %13s %13s %12s %s" % (
        "Ruta", "KPI", "MIS", "Ny rapport", "Core", "Diff ny-MIS", "Status"))
    print("-" * 92)

    rows = []
    seen_boxes = set()
    for kpi_name, code in sorted(BOX_BY_KPI.items(), key=lambda kv: kv[1]):
        # Box 06 has two KPI names depending on data version; report it once.
        if code in seen_boxes:
            continue
        seen_boxes.add(code)
        # The generated report keeps the MIS KPI name as its line code
        # (FORSMOMSEJANNAN), while core uses se_NN. Look up both ways --
        # otherwise every generated amount reads as 0.
        new_val = new.get(kpi_name)
        if new_val is None:
            new_val = new.get(kpi_name.upper())
        if new_val is None:
            new_val = new.get(code)
        if kpi_name not in mis and new_val is None and code not in core:
            continue
        row = {
            'box': code.replace('se_', ''),
            'kpi': kpi_name,
            'mis': round(mis.get(kpi_name, 0.0), 2),
            'new': round(new_val or 0.0, 2),
            'core': round(core.get(code, 0.0), 2),
        }
        row['diff'] = round(row['new'] - row['mis'], 2)
        row['ok'] = abs(row['diff']) <= tol
        if row['ok']:
            row['klass'], row['note'] = OKLAR, ''
            row['status'] = 'OK'
        else:
            row['klass'], row['note'] = classify(row, ctx)
            row['status'] = 'AVVIKER'
        rows.append(row)
        print("%-5s %-24s %13.2f %13.2f %13.2f %12.2f %s" % (
            row['box'], kpi_name[:24], row['mis'], row['new'],
            row['core'], row['diff'], row['status']))

    differing = [r for r in rows if not r['ok']]
    print("-" * 92)
    print("%d rutor jämförda, %d avviker (tolerans %.2f kr)"
          % (len(rows), len(differing), tol))
    if differing:
        print("")
        for row in differing:
            print("  Ruta %-3s %-22s klass=%-28s %s" % (
                row['box'], row['kpi'][:22], row['klass'], row['note']))
    oklara = [r for r in rows if r['klass'] == OKLAR and not r['ok']]
    if oklara:
        print("")
        print("  %d OKLARA avvikelser — verifieringen kan inte godkännas "
              "förrän de är klassade." % len(oklara))

    dead = []
    if not mis or not any(abs(v) > 0.01 for v in mis.values()):
        dead.append('MIS')
    if not new or not any(abs(v) > 0.01 for v in new.values()):
        dead.append('Ny rapport')
    if dead:
        print("")
        print("  MOTORN/N RÄKNAR INTE: %s. Jämförelsen är inte giltig som "
              "godkännande." % ', '.join(dead))
    return rows


def compare_balance(env, date_from, date_to, company=None, tol=DEFAULT_TOLERANCE):
    """Three-way comparison for the balance sheet and P&L.

    Same shape as ``compare`` but without the KPI mapping -- the generated
    report and the core report share codes for these.
    """
    company = company or env.company
    out = {}
    for kind, label in (('br', 'BALANSRÄKNING'), ('rr', 'RESULTATRÄKNING')):
        generated = _generated_report(env, kind)
        if not generated:
            print("%s: ingen genererad rapport hittad" % label)
            continue
        opts = _options(env, date_from, date_to, True)
        amounts = _lines_to_amounts(generated, opts)
        print("=" * 78)
        print("%s — %s" % (label, generated.name))
        print("Period: %s .. %s   Rader: %d" % (date_from, date_to, len(amounts)))
        nonzero = {k: v for k, v in amounts.items() if abs(v) > 0.01}
        print("Rader med belopp: %d" % len(nonzero))
        for code, value in sorted(nonzero.items())[:40]:
            print("  %-42s %14.2f" % (code[:42], value))
        out[kind] = amounts
    return out


# ----------------------------------------------------------------------
# Performance (3.1, 3.1b, 3.1c, 3.2)
# ----------------------------------------------------------------------
def _time_call(fn, samples, limit_seconds=None):
    """Run ``fn`` ``samples`` times, returning per-run seconds."""
    times = []
    started = time.perf_counter()
    for _ in range(samples):
        if limit_seconds and (time.perf_counter() - started) > limit_seconds:
            raise Timeout("tidsgränsen %ss överskreds" % limit_seconds)
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return times


def _stats(times):
    ordered = sorted(times)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return {'first': times[0], 'min': ordered[0], 'median': median,
            'max': ordered[-1], 'n': n}


def benchmark(env, date_from, date_to, company=None, samples=5, unfold=True,
              limit_seconds=None):
    """Time one _get_lines() call per alternative, per report.

    The alternatives are what a user actually does today (design D3b):
    the old engine (fresh instance), core, and the new report.
    """
    company = company or env.company
    mode = 'utfällt' if unfold else 'hopfällt'
    opts = _options(env, date_from, date_to, unfold)

    targets = []
    for kind, label in (('md', 'Momsdeklaration'),
                        ('br', 'Balansräkning'),
                        ('rr', 'Resultaträkning')):
        gen = _generated_report(env, kind)
        if gen:
            targets.append((label, 'ny rapport', gen))
    core = _source_report(env)
    if core:
        targets.append(('Momsdeklaration', 'core', core))
    mis_report = env.ref('l10n_se_mis.report_md', raise_if_not_found=False)
    if mis_report:
        try:
            _mis_amounts(env, date_from, date_to, company)
            instance = env['mis.report.instance'].search([
                ('report_id', '=', mis_report.id),
                ('company_id', '=', company.id)], limit=1)
            if instance:
                targets.append(('Momsdeklaration', 'gammal (sparad)', instance))
            else:
                targets.append(('Momsdeklaration', 'gammal (ny instans)', None))
        except Exception as exc:  # noqa: BLE001 - report, don't crash
            print("MIS: kunde inte förberedas: %s" % exc)

    print("=" * 92)
    print("PRESTANDA — interaktiv svarstid (%s)" % mode)
    print("Period: %s .. %s   %d körningar per mätpunkt"
          % (date_from, date_to, samples))
    print("Ett anrop = ett _get_lines() = ett RPC från frontend.")
    print("=" * 92)
    print("%-20s %-22s %10s %10s %10s %10s" % (
        "Rapport", "Motor", "första", "min", "median", "max"))
    print("-" * 92)

    results = []
    for label, engine, target in targets:
        if target is None:
            print("%-20s %-22s %10s" % (label, engine, "(kräver instans)"))
            continue
        if engine.startswith('gammal'):
            def call(t=target):
                env['mis.report.instance'].browse(t.id)._compute_matrix()
        else:
            def call(t=target, o=opts):
                env.invalidate_all()
                t._get_lines(o)
        try:
            times = _time_call(call, samples, limit_seconds)
        except Timeout as exc:
            print("%-20s %-22s AVBRUTEN: %s" % (label, engine, exc))
            results.append({'report': label, 'engine': engine,
                            'aborted': str(exc)})
            continue
        st = _stats(times)
        print("%-20s %-22s %9.0fms %9.0fms %9.0fms %9.0fms" % (
            label, engine, st['first'] * 1000, st['min'] * 1000,
            st['median'] * 1000, st['max'] * 1000))
        results.append(dict(st, report=label, engine=engine,
                            mode=mode))
    return results


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def run(env, date_from, date_to, company=None, samples=5,
        limit_seconds=None, tol=DEFAULT_TOLERANCE, full=True):
    """Correctness, then performance, in one call."""
    rows = compare(env, date_from, date_to, company=company, tol=tol)
    if full:
        compare_balance(env, date_from, date_to, company=company, tol=tol)
        print("")
        benchmark(env, date_from, date_to, company=company,
                  samples=samples, limit_seconds=limit_seconds)
    return rows


def compare_current_period(env):
    """Convenience: compare the current fiscal year to date."""
    from odoo import fields
    today = fields.Date.context_today(env.user)
    start = today.replace(month=1, day=1)
    return compare(env, start, today)
