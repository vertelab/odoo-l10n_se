# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################
"""Importera tolkad SIE 4 till Odoo 18.

Ordning:
  1. Konton (skapa de som saknas, med BAS-typ)
  2. Journaler (en per verifikationsserie)
  3. Ingående balans som en öppningsverifikation
  4. Verifikationer, postade

Allt går genom ``l10n_se.fortnox.migration.account.resolver`` så att saknade konton
och journaler aldrig kraschar importen.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .sie_parser import SieParser, decode_sie

_logger = logging.getLogger(__name__)


class SieImporter(models.AbstractModel):
    _name = 'l10n_se.fortnox.migration.sie.importer'
    _description = 'SIE 4 Importer (Odoo 18)'

    # ------------------------------------------------------------------
    # Hjälpare
    # ------------------------------------------------------------------

    @api.model
    def _sie_date(self, value):
        """SIE-datum är YYYYMMDD."""
        if not value or len(str(value)) != 8:
            return False
        v = str(value)
        return '%s-%s-%s' % (v[0:4], v[4:6], v[6:8])

    @api.model
    def parse(self, blob):
        """Tolka SIE-fil utan att skriva något. Returnerar SieParser."""
        text, encoding = decode_sie(blob)
        parser = SieParser(text)
        parser.encoding = encoding
        return parser

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    @api.model
    def import_sie(self, blob, company=None, options=None):
        """Importera SIE 4.

        :param blob: rå filbytes
        :param company: res.company (default env.company)
        :param options: dict med import_accounts, import_opening,
                        import_vouchers, dry_run
        :return: rapport-dict
        """
        company = company or self.env.company
        options = options or {}
        do_accounts = options.get('import_accounts', True)
        do_opening = options.get('import_opening', True)
        do_vouchers = options.get('import_vouchers', True)
        dry_run = options.get('dry_run', False)

        parser = self.parse(blob)
        report = {
            'encoding': parser.encoding,
            'sie_type': parser.sie_type,
            'company': parser.company_name,
            'accounts_total': len(parser.accounts),
            'accounts_created': [],
            'journals_created': [],
            'opening_created': 0,
            'vouchers_created': 0,
            'vouchers_skipped': 0,
            'vouchers_duplicate': 0,
            'opening_skipped': False,
            'problems': parser.validate(),
            'errors': list(parser.errors),
        }

        if parser.sie_type not in (4, None):
            report['errors'].append(
                'SIE-typen är %s — rekommenderat är typ 4 (full bokföring).'
                % parser.sie_type
            )

        resolver = self.env['l10n_se.fortnox.migration.account.resolver'].with_company(company)
        Account = self.env['account.account'].with_company(company)
        Move = self.env['account.move'].with_company(company)

        # ---- 1. Konton ------------------------------------------------
        if do_accounts:
            for number, meta in parser.accounts.items():
                acct, created = resolver.resolve_account(
                    number, name=meta.get('name'), company=company,
                )
                if created:
                    report['accounts_created'].append(number)

        # ---- 2. Journaler ---------------------------------------------
        series_seen = set()
        for v in parser.vouchers:
            s = v['series']
            if not s or s in series_seen:
                continue
            series_seen.add(s)
            _j, created = resolver.resolve_journal(s, company=company)
            if created:
                report['journals_created'].append(s)

        if dry_run:
            report['dry_run'] = True
            return report

        # ---- 3. Ingående balans ---------------------------------------
        if do_opening and parser.opening:
            # Använd det första räkenskapsåret i filen
            years = sorted({y for (y, _a) in parser.opening.keys()})
            year = years[0] if years else None
            if year:
                # Öppningsverifikationen dateras till räkenskapsårets första dag
                fy = next((f for f in parser.fiscal_years if f[0] == year), None)
                open_date = self._sie_date(fy[1]) if fy else '%s-01-01' % year
                journal, _c = resolver.resolve_journal('IB', name='Ingående balans',
                                                      journal_type='general',
                                                      company=company)
                lines = []
                for (y, account), amount in parser.opening.items():
                    if y != year or abs(amount) < 0.005:
                        continue
                    acct, _c = resolver.resolve_account(account, company=company)
                    if not acct:
                        continue
                    lines.append((0, 0, {
                        'account_id': acct.id,
                        'debit': amount if amount > 0 else 0.0,
                        'credit': -amount if amount < 0 else 0.0,
                        'name': _('Ingående balans %s') % year,
                    }))
                if lines:
                    total = sum(l[2]['debit'] - l[2]['credit'] for l in lines)
                    if abs(total) > 0.05:
                        report['errors'].append(
                            'Ingående balans balanserar inte: %.2f' % total
                        )
                    elif Move.search_count([
                        ('ref', '=', _('SIE IB %s') % year),
                        ('journal_id', '=', journal.id),
                    ]):
                        report['opening_skipped'] = True
                    else:
                        move = Move.create({
                            'journal_id': journal.id,
                            'date': open_date,
                            'ref': _('SIE IB %s') % year,
                            'line_ids': lines,
                        })
                        move.action_post()
                        report['opening_created'] = len(lines)

        # ---- 4. Verifikationer ----------------------------------------
        if do_vouchers:
            for v in parser.vouchers:
                date = self._sie_date(v['date'])
                if not date:
                    report['vouchers_skipped'] += 1
                    continue

                total = sum(l['amount'] for l in v['lines'])
                if abs(total) > 0.005:
                    report['vouchers_skipped'] += 1
                    report['errors'].append(
                        'Verifikation %s/%s obalanserad (%.2f) — hoppade över'
                        % (v['series'], v['number'], total)
                    )
                    continue

                ref = '%s %s/%s' % (_('SIE'), v['series'], v['number'])
                if Move.search_count([('ref', '=', ref)]):
                    report['vouchers_skipped'] += 1
                    report['vouchers_duplicate'] = report.get('vouchers_duplicate', 0) + 1
                    continue

                journal, _c = resolver.resolve_journal(v['series'], company=company)
                lines = []
                for l in v['lines']:
                    acct, _c = resolver.resolve_account(l['account'], company=company)
                    if not acct:
                        continue
                    amount = l['amount']
                    lines.append((0, 0, {
                        'account_id': acct.id,
                        'debit': amount if amount > 0 else 0.0,
                        'credit': -amount if amount < 0 else 0.0,
                        'name': l.get('text') or v.get('text') or '',
                    }))

                if not lines:
                    report['vouchers_skipped'] += 1
                    continue

                move = Move.create({
                    'journal_id': journal.id,
                    'date': date,
                    'ref': ref,
                    'line_ids': lines,
                })
                move.action_post()
                report['vouchers_created'] += 1

        return report
