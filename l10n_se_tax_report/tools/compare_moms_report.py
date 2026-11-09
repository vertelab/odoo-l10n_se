# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Compare the MIS-based VAT declaration against the account.report one.

Run from the Odoo shell:

    LC_ALL=C sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d <db> --no-http \\
        < compare_moms_report.py

or interactively:

    >>> from odoo.addons.l10n_se_tax_report.tools.compare_moms_report import compare
    >>> compare(env, '2026-01-01', '2026-12-31')

Why this exists
---------------
The Swedish VAT boxes are computed in two very different ways:

* MIS Builder selects on the **tax name** (``('tax_line_id.name', '=', 'MP1')``)
  or on account codes (``bal[3000,…]``).
* ``account.report`` selects on **tax tags** (``+se_10``) or account codes.

Both are legitimate; they are simply not the same calculation. Before
``l10n_se_mis`` is retired, every box must be shown to produce the same amount
on real data. This tool prints that comparison so the difference is a number
in a table instead of a surprise in a customer's VAT return.
"""

import logging

_logger = logging.getLogger(__name__)

# MIS KPI name -> core report code. Derived from the two data files:
#   l10n_se_mis/data/mis_momsdeklaration_report.xml  (kpi name + description)
#   l10n_se/data/account_tax_report_data.xml         (line code + name)
# The description prefix ('#05', '#48', …) is the box number in both.
BOX_BY_KPI = {
    'ForsMomsEjAnnan': 'se_05',
    'Momspliktiga': 'se_06',
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


def _mis_amounts(env, date_from, date_to, company):
    """Per-KPI amounts from the MIS declaration report."""
    mis_report = env.ref('l10n_se_mis.report_md', raise_if_not_found=False)
    if not mis_report:
        return {}, 'l10n_se_mis.report_md not found'

    instance = env['mis.report.instance'].search([
        ('report_id', '=', mis_report.id),
        ('company_id', '=', company.id),
    ], limit=1)
    if not instance:
        # No configured instance: build a throw-away one for the period.
        # A period row requires a name, and mode 'fix' + manual dates is what
        # the declaration code itself uses when it re-points the period.
        instance = env['mis.report.instance'].create({
            'name': 'compare-tmp',
            'report_id': mis_report.id,
            'company_id': company.id,
            'period_ids': [(0, 0, {
                'name': 'compare',
                'sequence': 1,
                'mode': 'fix',
                'manual_date_from': date_from,
                'manual_date_to': date_to,
            })],
        })
    else:
        for period in instance.period_ids:
            period.write({
                'manual_date_from': date_from,
                'manual_date_to': date_to,
            })

    amounts = {}
    matrix = instance._compute_matrix()
    for row in matrix.iter_rows():
        vals = [c.val for c in row.iter_cells()]
        if not vals or not isinstance(vals[0], (int, float)):
            continue
        amounts[row.kpi.name] = float(vals[0])
    return amounts, None


def _report_amounts(env, date_from, date_to, company):
    """Per-code amounts from the core Swedish tax report."""
    report = env['account.report'].search([
        ('country_id.code', '=', 'SE'),
        ('name', 'in', ('skatterapport', 'Tax Report', 'Momsdeklaration')),
    ], limit=1)
    if not report:
        return {}, report, 'No Swedish account.report found'

    options = {
        'date': {'date_from': date_from, 'date_to': date_to},
        'company_ids': [company.id],
        'unfold_all': True,
    }
    warnings = {}
    lines = report._get_lines(options, warnings=warnings)
    amounts = {}
    for line in lines:
        code = line.get('code')
        if not code:
            continue
        columns = line.get('columns') or []
        if columns:
            amounts[code] = float(columns[0].get('no_format') or 0.0)
    return amounts, report, (warnings or None)


def compare(env, date_from, date_to, company=None, tol=0.5):
    """Print a per-box comparison table. Returns a list of row dicts."""
    company = company or env.company
    mis, mis_error = _mis_amounts(env, date_from, date_to, company)
    rep, report, rep_error = _report_amounts(env, date_from, date_to, company)

    print("=" * 78)
    print("Momsdeklaration — MIS kontra account.report")
    print("Företag: %s   Period: %s .. %s" % (company.name, date_from, date_to))
    print("=" * 78)
    if mis_error:
        print("MIS: %s" % mis_error)
    if rep_error:
        print("account.report: %s" % rep_error)
    if not mis and not rep:
        print("Inga belopp att jämföra.")
        return []

    print("%-6s %-24s %14s %14s %14s %s" % (
        "Ruta", "KPI", "MIS", "account.report", "Differens", "Status"))
    print("-" * 78)

    rows = []
    for kpi_name, code in sorted(BOX_BY_KPI.items(), key=lambda kv: kv[1]):
        mis_val = mis.get(kpi_name)
        rep_val = rep.get(code)
        if mis_val is None and rep_val is None:
            continue
        mis_val = mis_val or 0.0
        rep_val = rep_val or 0.0
        diff = round(rep_val - mis_val, 2)
        status = 'OK' if abs(diff) <= tol else 'AVVIKER'
        rows.append({
            'box': code.replace('se_', ''),
            'kpi': kpi_name,
            'mis': mis_val,
            'report': rep_val,
            'diff': diff,
            'status': status,
        })
        print("%-6s %-24s %14.2f %14.2f %14.2f %s" % (
            code.replace('se_', ''), kpi_name, mis_val, rep_val, diff, status))

    differing = [r for r in rows if r['status'] != 'OK']
    print("-" * 78)
    print("%d rutor jämförda, %d avviker" % (len(rows), len(differing)))
    if differing:
        print("\nRutor som avviker (ska åtgärdas eller motiveras i design.md):")
        for row in differing:
            print("  Ruta %s (%s): MIS %.2f, account.report %.2f, diff %.2f" % (
                row['box'], row['kpi'], row['mis'], row['report'], row['diff']))
    return rows


def compare_current_period(env):
    """Convenience: compare the current fiscal year to date."""
    from odoo import fields
    today = fields.Date.context_today(env.user)
    start = today.replace(month=1, day=1)
    return compare(env, start, today)
