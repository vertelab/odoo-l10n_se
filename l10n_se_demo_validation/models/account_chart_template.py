# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Swedish demo data for the accounting chart template.

Why this module exists
======================

``account/demo/account_demo.py`` builds demo journal entries from generic
chart-of-accounts codes.  ``_get_demo_data_products()`` forces every demo
product's ``property_account_income_id`` / ``property_account_expense_id`` to
the company defaults, which on a Swedish BAS chart are ``a3001`` / ``a4001``.
Those exist in the parent template ``extended_se`` but **not** in
``extended_se_K2`` / ``extended_se_K3`` (those carry 1xxx-2xxx and 5xxx-8xxx;
3xxx/4xxx live in the parent).  ``_load_data()`` then logs

    "Failed when trying to recover %s for field=%s"

and creates the line with ``account_id = False`` — an unbalanced move.

How Odoo actually triggers demo data (important)
================================================

There are **two distinct entry points**, and they behave differently:

1. ``ir.demo.install_demo`` (the "Load demo data" link in Settings) calls
   ``odoo.modules.loading.force_demo()``.  That function only loads each
   module's ``demo`` XML files.  It does **not** call
   ``account.chart.template._get_demo_data()`` — the accounting demo payload
   is only reachable through ``_install_demo()``.

2. ``account.chart.template._load(..., install_demo=True)`` loads the chart
   and then calls ``_install_demo()`` -> ``_get_demo_data()``.  This is what
   ``try_loading()`` does when the chart is loaded for the first time.

   **Trap:** ``_load()`` sets ``install_demo = False`` when
   ``reload_template`` is true (i.e. the company already has that chart).
   So calling ``try_loading()`` on a company that already uses the Swedish
   chart silently skips all demo data.

This module therefore provides:

* ``_get_demo_data()`` — replaces the generic accounting payload with a
  Swedish one built from accounts resolved for the company's own chart.
  Works for entry point 2.
* ``action_install_swedish_demo()`` — a button (and a Settings entry) that
  explicitly calls ``_install_demo()`` on the current company, bypassing the
  ``reload_template`` trap.  Works for entry point 1 and for any database
  where the chart is already loaded.
* ``demo/demo_company_se.xml`` — for ``repo_apply`` of a fresh demo
  database: sets SEK + Sweden on the main company *before* the chart is
  loaded, so ``try_loading`` runs with ``reload_template = False``.

The override is a no-op on non-Swedish charts, so it is safe to install
everywhere.
"""

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Chart template codes handled by this module.
SE_TEMPLATE_PREFIX = 'extended_se'

#: Accounts that are safe to post demo entries against, per chart template.
#: The first existing code wins.  ``account_type`` is the fallback when none
#: of the codes exist (e.g. a customer-specific chart).
DEMO_ACCOUNTS = {
    'receivable': (['1511', '1510'], 'asset_receivable'),
    'payable': (['2441', '2440'], 'liability_payable'),
    'income_25': (['3100', '3001', '3000'], 'income'),
    'expense_goods': (['4200', '4000', '4001'], 'expense_direct_cost'),
    'expense_office': (['6100', '6110', '6990'], 'expense'),
    'expense_tele': (['6200', '6210', '6990'], 'expense'),
    'expense_rent': (['5010', '5011', '5000'], 'expense'),
    'expense_bank': (['6570', '6990', '6900'], 'expense'),
    'bank': (['1940', '1930', '1910'], 'asset_cash'),
    'cash': (['1911', '1910'], 'asset_cash'),
    'tax_output': (['2610', '2611', '2650'], 'liability_current'),
    'tax_input': (['2640', '2641', '2650'], 'liability_current'),
}

#: xml_ids of the moves created by :meth:`_l10n_se_demo_moves`.
DEMO_MOVE_KEYS = (
    'l10n_se_demo_invoice_customer',
    'l10n_se_demo_bill_vendor',
    'l10n_se_demo_bank_fee',
    'l10n_se_demo_rent',
)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _l10n_se_is_swedish(self, company):
        """Return True when *company* uses a Swedish chart template."""
        if not company:
            return False
        template = company.chart_template or ''
        if template.startswith(SE_TEMPLATE_PREFIX):
            return True
        return (company.account_fiscal_country_id.code == 'SE'
                or company.country_id.code == 'SE')

    @api.model
    def _l10n_se_demo_account(self, key, company):
        """Resolve a demo account for *company*.

        Tries the candidate codes from :data:`DEMO_ACCOUNTS` first, then falls
        back to a search on ``account_type``.  Returns an empty recordset when
        nothing suitable exists — callers must handle that instead of writing
        ``account_id = False``.
        """
        codes, account_type = DEMO_ACCOUNTS[key]
        Account = self.env['account.account'].with_company(company)
        domain_company = Account._check_company_domain(company)

        for code in codes:
            account = Account.search(
                [*domain_company, ('code', '=', code)], limit=1)
            if account:
                return account

        account = Account.search(
            [*domain_company, ('account_type', '=', account_type)], limit=1)
        if not account:
            _logger.warning(
                'l10n_se_demo_validation: no account found for demo key %r '
                '(codes=%s, type=%s) on company %s — demo line skipped',
                key, codes, account_type, company.display_name)
        return account

    @api.model
    def _l10n_se_demo_journal(self, company, journal_type):
        """Return the first journal of *journal_type* for *company*."""
        return self.env['account.journal'].search(
            [*self.env['account.journal']._check_company_domain(company),
             ('type', '=', journal_type)], limit=1)

    # ------------------------------------------------------------------
    # Demo data override (entry point 2: try_loading with install_demo)
    # ------------------------------------------------------------------
    @api.model
    def _get_demo_data(self, company=False):
        """Replace generic accounting demo data with Swedish data.

        On a non-Swedish chart the parent implementation is returned
        untouched.  On a Swedish chart the account-move, bank-statement and
        reconcile-model blocks are replaced; partner/product data is kept
        (it carries no chart dependency once the tax linkage is dropped).
        """
        company = company or self.env.company
        data = super()._get_demo_data(company)

        if not self._l10n_se_is_swedish(company):
            return data

        _logger.info(
            'l10n_se_demo_validation: replacing generic accounting demo data '
            'with Swedish data for company %s (chart %s)',
            company.display_name, company.chart_template)

        data['account.move'] = self._l10n_se_demo_moves(company)
        data['account.bank.statement'] = self._l10n_se_demo_statement(company)
        data['account.bank.statement.line'] = {}
        data['account.reconcile.model'] = {}
        # Attachments / mail messages reference the generic demo moves which we
        # just removed — drop them so no orphan chatter is created.
        data['ir.attachment'] = {}
        data['mail.message'] = {}
        data['mail.activity'] = {}
        return data

    @api.model
    def _l10n_se_demo_moves(self, company):
        """Build a small, balanced Swedish demo ledger.

        Every move is a balanced two- or three-line entry against accounts
        that were resolved for *company*, so ``_post_load_demo_data`` can post
        them without hitting a missing account.
        """
        today = fields.Date.today()
        first_of_month = today.replace(day=1)

        receivable = self._l10n_se_demo_account('receivable', company)
        payable = self._l10n_se_demo_account('payable', company)
        income = self._l10n_se_demo_account('income_25', company)
        expense_office = self._l10n_se_demo_account('expense_office', company)
        expense_rent = self._l10n_se_demo_account('expense_rent', company)
        expense_bank = self._l10n_se_demo_account('expense_bank', company)
        bank = self._l10n_se_demo_account('bank', company)

        # A move needs both counterpart accounts; skip the block entirely if
        # the chart is too minimal to hold a receivable/payable pair.
        if not (receivable and payable and income):
            _logger.warning(
                'l10n_se_demo_validation: chart of company %s lacks the '
                'receivable/payable/income accounts needed for Swedish demo '
                'data — no demo journal entries created',
                company.display_name)
            return {}

        partner_customer = self.env.ref('base.res_partner_12', raise_if_not_found=False)
        partner_vendor = self.env.ref('base.res_partner_2', raise_if_not_found=False)

        moves = {}

        # 1. Customer invoice — 25 % VAT, balanced three-line entry.
        tax_output = self._l10n_se_demo_account('tax_output', company)
        line_ids = [
            Command.create({
                'name': 'Demo: konsultarvode',
                'account_id': receivable.id,
                'debit': 12500.0,
                'credit': 0.0,
                'partner_id': partner_customer.id if partner_customer else False,
            }),
            Command.create({
                'name': 'Demo: konsultarvode',
                'account_id': income.id,
                'debit': 0.0,
                'credit': 10000.0,
            }),
        ]
        if tax_output:
            line_ids.append(Command.create({
                'name': 'Demo: utgående moms 25 %',
                'account_id': tax_output.id,
                'debit': 0.0,
                'credit': 2500.0,
            }))
        else:
            # No VAT account: book the invoice VAT-free so it stays balanced.
            line_ids[0]['debit'] = 10000.0
        moves['l10n_se_demo_invoice_customer'] = {
            'move_type': 'entry',
            'date': first_of_month,
            'ref': 'DEMO/SE/KUNDFAKTURA',
            'line_ids': line_ids,
        }

        # 2. Vendor bill — office supplies, 25 % VAT.
        tax_input = self._l10n_se_demo_account('tax_input', company)
        line_ids = [
            Command.create({
                'name': 'Demo: kontorsmaterial',
                'account_id': expense_office.id,
                'debit': 2000.0,
                'credit': 0.0,
            }),
        ]
        credit_total = 2000.0
        if tax_input:
            line_ids.append(Command.create({
                'name': 'Demo: ingående moms 25 %',
                'account_id': tax_input.id,
                'debit': 500.0,
                'credit': 0.0,
            }))
            credit_total = 2500.0
        line_ids.append(Command.create({
            'name': 'Demo: leverantörsskuld',
            'account_id': payable.id,
            'debit': 0.0,
            'credit': credit_total,
            'partner_id': partner_vendor.id if partner_vendor else False,
        }))
        moves['l10n_se_demo_bill_vendor'] = {
            'move_type': 'entry',
            'date': first_of_month,
            'ref': 'DEMO/SE/LEVERANTÖRSFAKTURA',
            'line_ids': line_ids,
        }

        # 3. Bank fee — simple balanced misc entry.
        if expense_bank and bank:
            moves['l10n_se_demo_bank_fee'] = {
                'move_type': 'entry',
                'date': first_of_month,
                'ref': 'DEMO/SE/BANKAVGIFT',
                'line_ids': [
                    Command.create({
                        'name': 'Demo: bankavgift',
                        'account_id': expense_bank.id,
                        'debit': 250.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'Demo: bankavgift',
                        'account_id': bank.id,
                        'debit': 0.0,
                        'credit': 250.0,
                    }),
                ],
            }

        # 4. Rent — balanced misc entry.
        if expense_rent and bank:
            moves['l10n_se_demo_rent'] = {
                'move_type': 'entry',
                'date': first_of_month,
                'ref': 'DEMO/SE/LOKALHYRA',
                'line_ids': [
                    Command.create({
                        'name': 'Demo: lokalhyra',
                        'account_id': expense_rent.id,
                        'debit': 8000.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'Demo: lokalhyra',
                        'account_id': bank.id,
                        'debit': 0.0,
                        'credit': 8000.0,
                    }),
                ],
            }

        return moves

    @api.model
    def _l10n_se_demo_statement(self, company):
        """A bank statement that only references existing accounts.

        The generic implementation books an "Initial balance" line whose
        counter-account is the journal suspense account — that one is always
        created by ``_setup_utility_bank_accounts`` and is therefore safe.
        We keep a single, minimal statement.
        """
        bank_journal = self._l10n_se_demo_journal(company, 'bank')
        if not bank_journal:
            return {}
        return {
            'l10n_se_demo_bank_statement': {
                'name': '%s - %s-01-01/1' % (
                    bank_journal.name, fields.Date.today().year),
                'balance_start': 0.0,
                'balance_end_real': 5000.0,
                'line_ids': [
                    Command.create({
                        'journal_id': bank_journal.id,
                        'payment_ref': 'Demo: ingående balans',
                        'amount': 5000.0,
                        'date': fields.Date.today().replace(month=1, day=1),
                    }),
                ],
            },
        }

    # ------------------------------------------------------------------
    # Post-load: make sure the demo moves actually post
    # ------------------------------------------------------------------
    def _post_load_demo_data(self, company=False):
        """Post the Swedish demo moves.

        The parent implementation (``account/demo/account_demo.py``) posts the
        *generic* demo invoices by xml_id::

            invoices = (self.ref('demo_invoice_1') + self.ref('demo_invoice_2')
                        + ...)

        Those xml_ids do not exist on a Swedish chart because
        ``_get_demo_data()`` replaced the whole ``account.move`` payload.  The
        parent call therefore raises ``ValueError: External ID not found`` and
        aborts the demo installation before our own moves are posted.

        We skip the parent entirely on a Swedish chart and post our own moves
        instead.  Each move is posted in its own savepoint so one failure does
        not roll back the rest.
        """
        company = company or self.env.company
        if not self._l10n_se_is_swedish(company):
            return super()._post_load_demo_data(company)

        for xml_id in DEMO_MOVE_KEYS:
            move = self.ref('account.%s_%s' % (company.id, xml_id),
                            raise_if_not_found=False)
            if not move:
                _logger.warning(
                    'l10n_se_demo_validation: demo move %s not found for '
                    'company %s', xml_id, company.display_name)
                continue
            if move.state == 'posted':
                # Already posted by a previous run — nothing to do.
                continue
            try:
                with self.env.cr.savepoint():
                    move.action_post()
            except Exception:  # noqa: BLE001 - demo data must never abort install
                _logger.warning(
                    'l10n_se_demo_validation: could not post demo move %s',
                    xml_id, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Entry point 1: explicit demo installation
    # ------------------------------------------------------------------
    @api.model
    def action_install_swedish_demo(self, company=False):
        """Install the Swedish accounting demo data on *company*.

        This is the public entry point for databases where the chart is
        already loaded — the case the "Load demo data" link in Settings does
        not cover, because ``force_demo()`` never reaches
        ``_get_demo_data()``.

        Safe to call repeatedly: ``_load_data(..., ignore_duplicates=True)``
        skips records whose xml_id already exists.
        """
        company = company or self.env.company
        if not self._l10n_se_is_swedish(company):
            raise UserError(_(
                'Company "%(company)s" does not use a Swedish chart of '
                'accounts (current: %(chart)s). Install a Swedish chart '
                'first.',
                company=company.display_name,
                chart=company.chart_template or _('none'),
            ))

        _logger.info(
            'l10n_se_demo_validation: installing Swedish demo data on %s',
            company.display_name)
        self._install_demo(company)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Swedish demo data'),
                'message': _(
                    'Demo journal entries were created on "%s".',
                    company.display_name),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
