# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################
"""Resolverare för konton och journaler vid migrering.

Problemet: Fortnox-data refererar till konton (t.ex. 1930, 2440, 3010) och
verifikationsserier (A, B, F, L) som inte nödvändigtvis finns i Odoo. En naiv
import kraschar på ForeignKey-fel eller skapar osynliga halvposter.

Den här modulen löser det i tre steg:

1. Slå upp kontot i Odoo (per företag, via ``code``).
2. Finns det inte — skapa det med rätt ``account_type``, härlett ur
   BAS-kontonumret (svensk standard) eller Fortnox ``Type``.
3. Kan typen inte avgöras — skapa som ``asset_current`` och logga varningen
   så användaren kan rätta i efterhand.

Journaler: Fortnox verifikationsserier mappas mot Odoo-journaler. Saknas
journalen skapas en ``general``-journal med samma kod. Sälj-/inköpsjournaler
(F/L) mappas mot befintliga ``sale``/``purchase`` om de finns.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# BAS-kontoplan: intervall -> Odoo account_type
# ----------------------------------------------------------------------
# BAS 2024. Kontoklass 1-8. Vi använder intervall snarare än exakta nummer
# eftersom BAS tillåter fria konton inom klasserna.
BAS_RANGES = [
    # (från, till, account_type, beskrivning)
    (1000, 1099, 'asset_current', 'Immateriella anläggningstillgångar'),
    (1100, 1199, 'asset_current', 'Byggnader och mark'),
    (1200, 1299, 'asset_fixed', 'Maskiner och inventarier'),
    (1300, 1399, 'asset_fixed', 'Finansiella anläggningstillgångar'),
    (1400, 1499, 'asset_current', 'Varulager'),
    (1500, 1599, 'asset_receivable', 'Kundfordringar'),
    (1600, 1699, 'asset_current', 'Övriga fordringar'),
    (1700, 1799, 'asset_prepayments', 'Förutbetalda kostnader'),
    (1800, 1899, 'asset_current', 'Övriga fordringar'),
    (1900, 1999, 'asset_cash', 'Kassa och bank'),
    (2000, 2099, 'equity', 'Eget kapital'),
    (2100, 2199, 'equity', 'Eget kapital (enskild firma)'),
    (2200, 2299, 'equity', 'Eget kapital (AB)'),
    (2300, 2399, 'equity', 'Eget kapital'),
    (2400, 2499, 'liability_current', 'Kortfristiga skulder'),
    (2500, 2599, 'liability_current', 'Skatteskulder'),
    (2600, 2699, 'liability_current', 'Moms och punktskatter'),
    (2700, 2799, 'liability_current', 'Personalens skatter'),
    (2800, 2899, 'liability_current', 'Övriga kortfristiga skulder'),
    (2900, 2999, 'liability_non_current', 'Långfristiga skulder'),
    (3000, 3099, 'income', 'Försäljning varor'),
    (3100, 3199, 'income', 'Försäljning tjänster'),
    (3200, 3299, 'income', 'Försäljning'),
    (3300, 3399, 'income', 'Försäljning'),
    (3400, 3499, 'income', 'Försäljning'),
    (3500, 3599, 'income', 'Fakturerade kostnader'),
    (3600, 3699, 'income', 'Övriga rörelseintäkter'),
    (3700, 3799, 'income', 'Övriga rörelseintäkter'),
    (3800, 3899, 'income', 'Övriga rörelseintäkter'),
    (3900, 3999, 'income_other', 'Övriga intäkter'),
    (4000, 4099, 'expense_direct_cost', 'Inköp varor'),
    (4100, 4199, 'expense_direct_cost', 'Inköp varor'),
    (4200, 4299, 'expense_direct_cost', 'Inköp material'),
    (4300, 4399, 'expense_direct_cost', 'Inköp material'),
    (4400, 4499, 'expense_direct_cost', 'Inköp varor'),
    (4500, 4599, 'expense_direct_cost', 'Inköp varor'),
    (4600, 4699, 'expense_direct_cost', 'Inköp varor'),
    (4700, 4799, 'expense_direct_cost', 'Inköp varor'),
    (4800, 4899, 'expense_direct_cost', 'Inköp varor'),
    (4900, 4999, 'expense_direct_cost', 'Inköp varor'),
    (5000, 5099, 'expense', 'Lokalkostnader'),
    (5100, 5199, 'expense', 'Lokalkostnader'),
    (5200, 5299, 'expense', 'Lokalkostnader'),
    (5300, 5399, 'expense', 'Lokalkostnader'),
    (5400, 5499, 'expense', 'Lokalkostnader'),
    (5500, 5599, 'expense', 'Lokalkostnader'),
    (5600, 5699, 'expense', 'Lokalkostnader'),
    (5700, 5799, 'expense', 'Lokalkostnader'),
    (5800, 5899, 'expense', 'Lokalkostnader'),
    (5900, 5999, 'expense', 'Lokalkostnader'),
    (6000, 6099, 'expense', 'Övriga rörelsekostnader'),
    (6100, 6199, 'expense', 'Övriga rörelsekostnader'),
    (6200, 6299, 'expense', 'Övriga rörelsekostnader'),
    (6300, 6399, 'expense', 'Övriga rörelsekostnader'),
    (6400, 6499, 'expense', 'Övriga rörelsekostnader'),
    (6500, 6599, 'expense', 'Övriga rörelsekostnader'),
    (6600, 6699, 'expense', 'Övriga rörelsekostnader'),
    (6700, 6799, 'expense', 'Övriga rörelsekostnader'),
    (6800, 6899, 'expense', 'Övriga rörelsekostnader'),
    (6900, 6999, 'expense', 'Övriga rörelsekostnader'),
    (7000, 7099, 'expense', 'Personalkostnader'),
    (7100, 7199, 'expense', 'Personalkostnader'),
    (7200, 7299, 'expense', 'Personalkostnader'),
    (7300, 7399, 'expense', 'Personalkostnader'),
    (7400, 7499, 'expense', 'Personalkostnader'),
    (7500, 7599, 'expense', 'Personalkostnader'),
    (7600, 7699, 'expense', 'Personalkostnader'),
    (7700, 7799, 'expense', 'Personalkostnader'),
    (7800, 7899, 'expense_depreciation', 'Avskrivningar'),
    (7900, 7999, 'expense', 'Övriga rörelsekostnader'),
    (8000, 8099, 'income_other', 'Finansiella intäkter'),
    (8100, 8199, 'income_other', 'Finansiella intäkter'),
    (8200, 8299, 'income_other', 'Finansiella intäkter'),
    (8300, 8399, 'expense', 'Finansiella kostnader'),
    (8400, 8499, 'expense', 'Finansiella kostnader'),
    (8500, 8599, 'expense', 'Finansiella kostnader'),
    (8600, 8699, 'expense', 'Finansiella kostnader'),
    (8700, 8799, 'expense', 'Finansiella kostnader'),
    (8800, 8899, 'expense', 'Bokslutsdispositioner'),
    (8900, 8999, 'expense', 'Skatter och årets resultat'),
]

# Fortnox egen Type-klassning som fallback
FORTNOX_TYPE_MAP = {
    'TILLGANGAR': 'asset_current',
    'ANLÄGGNINGSTILLGÅNGAR': 'asset_fixed',
    'OMSÄTTNINGSTILLGÅNGAR': 'asset_current',
    'KORTFRISTIGA FORDRINGAR': 'asset_receivable',
    'KASSA OCH BANK': 'asset_cash',
    'EGET KAPITAL': 'equity',
    'SKULDER': 'liability_current',
    'KORTFRISTIGA SKULDER': 'liability_current',
    'LÅNGFRISTIGA SKULDER': 'liability_non_current',
    'INTÄKTER': 'income',
    'RÖRELSEINTÄKTER': 'income',
    'KOSTNADER': 'expense',
    'RÖRELSEKOSTNADER': 'expense',
    'VARUKOSTNADER': 'expense_direct_cost',
    'PERSONALKOSTNADER': 'expense',
    'AVSKRIVNINGAR': 'expense_depreciation',
    'FINANSIELLA INTÄKTER': 'income_other',
    'FINANSIELLA KOSTNADER': 'expense',
}


class AccountResolver(models.AbstractModel):
    """Löser upp och skapar konton som saknas vid migrering."""

    _name = 'l10n_se.fortnox.migration.account.resolver'
    _description = 'Migration Account Resolver'

    # ------------------------------------------------------------------
    # Typ-härledning
    # ------------------------------------------------------------------

    @api.model
    def guess_account_type(self, number, fortnox_type=None):
        """Härled Odoo account_type ur kontonummer (BAS) eller Fortnox-typ."""
        try:
            num = int(str(number).strip())
        except (TypeError, ValueError):
            return 'asset_current', 'kunde inte tolka kontonummer'

        for start, end, acc_type, label in BAS_RANGES:
            if start <= num <= end:
                return acc_type, label

        if fortnox_type:
            key = str(fortnox_type).strip().upper()
            if key in FORTNOX_TYPE_MAP:
                return FORTNOX_TYPE_MAP[key], 'Fortnox-typ %s' % key

        return 'asset_current', 'okänt intervall'

    # ------------------------------------------------------------------
    # Konto
    # ------------------------------------------------------------------

    @api.model
    def resolve_account(self, number, name=None, fortnox_type=None,
                        company=None, create=True):
        """Hitta eller skapa konto. Returnerar (account, skapad)."""
        company = company or self.env.company
        code = str(number).strip()
        if not code:
            raise UserError(_('Kontonummer saknas.'))

        Account = self.env['account.account'].with_company(company)

        account = Account.search([('code', '=', code)], limit=1)
        if account:
            return account, False

        if not create:
            return Account.browse(), False

        acc_type, reason = self.guess_account_type(code, fortnox_type)
        vals = {
            'code': code,
            'name': name or _('Konto %s (migrerat)') % code,
            'account_type': acc_type,
            'company_ids': [(6, 0, [company.id])],
        }

        # Kundfordringar och leverantörsskulder måste tillåta avstämning
        if acc_type in ('asset_receivable', 'liability_payable'):
            vals['reconcile'] = True

        account = Account.create(vals)
        _logger.info(
            'Skapade konto %s "%s" som %s (%s)',
            code, vals['name'], acc_type, reason,
        )
        return account, True

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------

    @api.model
    def resolve_journal(self, code, name=None, journal_type=None,
                        company=None, create=True):
        """Hitta eller skapa journal för en Fortnox-verifikationsserie."""
        company = company or self.env.company
        code = (code or 'MISC').strip().upper()[:5]

        Journal = self.env['account.journal'].with_company(company)
        journal = Journal.search([('code', '=', code)], limit=1)
        if journal:
            return journal, False

        if not create:
            return Journal.browse(), False

        # Gissa typ ur seriekoden (svensk praxis)
        guessed = journal_type
        if not guessed:
            if code in ('F', 'K', 'S'):
                guessed = 'sale'
            elif code in ('L', 'I'):
                guessed = 'purchase'
            elif code in ('B', 'BG'):
                guessed = 'bank'
            elif code in ('K', 'C'):
                guessed = 'cash'
            else:
                guessed = 'general'

        vals = {
            'code': code,
            'name': name or _('Migrerad serie %s') % code,
            'type': guessed,
            'company_id': company.id,
        }
        journal = Journal.create(vals)
        _logger.info('Skapade journal %s (%s)', code, guessed)
        return journal, True

    # ------------------------------------------------------------------
    # Batch: förbered allt innan import
    # ------------------------------------------------------------------

    @api.model
    def prepare_from_fortnox(self, accounts, voucher_series, company=None):
        """Skapa alla konton och journaler som saknas, på en gång.

        Returnerar en rapport med vad som skapades, så användaren kan granska
        innan själva bokföringen importeras.
        """
        company = company or self.env.company
        report = {
            'accounts_created': [],
            'accounts_existing': 0,
            'journals_created': [],
            'journals_existing': 0,
            'warnings': [],
        }

        for acct in accounts:
            number = acct.get('Number')
            if number is None:
                continue
            _, created = self.resolve_account(
                number,
                name=acct.get('Description'),
                fortnox_type=acct.get('Type'),
                company=company,
            )
            if created:
                report['accounts_created'].append(str(number))
            else:
                report['accounts_existing'] += 1

        for series in voucher_series:
            code = series.get('Code')
            if not code:
                continue
            _, created = self.resolve_journal(
                code,
                name=series.get('Description'),
                company=company,
            )
            if created:
                report['journals_created'].append(code)
            else:
                report['journals_existing'] += 1

        if not report['accounts_created'] and not report['journals_created']:
            report['warnings'].append(
                _('Alla konton och journaler fanns redan — inget skapades.')
            )

        return report
