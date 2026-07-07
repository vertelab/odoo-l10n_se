# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tax Account Reconciliation — main model
# ---------------------------------------------------------------------------


class TaxAccountReconciliation(models.Model):
    _inherit = 'skatteverket.api'
    """Two-column reconciliation session for tax account (skattekonto).

    Inspired by Fortnox's "Stäm av konto" and Visma's monthly reconciliation:
    - Left column: booked journal entries on account 1630
    - Right column: imported transactions from Skatteverket API
    - Auto-match by amount ± tolerance days
    - Create settlement journal entry on the VAT journal
    - Batch reconciliation for past periods
    """
    _name = 'tax.account.reconciliation'
    _description = 'Tax Account Reconciliation'
    _order = 'date_from desc'

    # -- Header -------------------------------------------------------------
    name = fields.Char(
        string='Name', compute='_compute_name', store=True)
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='Tax Journal',
        required=True, ondelete='cascade',
        domain=[('type', '=', 'general')],
        help="The VAT journal (Momsjournal) used for settlement entries.")
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        related='journal_id.company_id', store=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id')

    date_from = fields.Date(
        string='From Date', required=True,
        help="Start date for the reconciliation period.")
    date_to = fields.Date(
        string='To Date', required=True,
        help="End date for the reconciliation period.")

    state = fields.Selection(
        selection=[('draft', 'Draft'), ('open', 'Open'),
                   ('done', 'Done'), ('cancel', 'Cancelled')],
        string='State', default='draft')

    # Balance tracking
    opening_balance = fields.Monetary(
        string='Opening Balance', currency_field='currency_id',
        compute='_compute_balances', store=True,
        help="Balance of account 1630 at start of period.")
    closing_balance = fields.Monetary(
        string='Closing Balance (Booked)', currency_field='currency_id',
        compute='_compute_balances', store=True,
        help="Balance of account 1630 after all booked entries.")
    skv_balance = fields.Monetary(
        string='SKV Balance', currency_field='currency_id',
        help="Balance reported by Skatteverket for this period.")
    balance_difference = fields.Monetary(
        string='Balance Difference', currency_field='currency_id',
        compute='_compute_balance_difference', store=True,
        help="Difference between booked closing balance and SKV balance.")

    # Counter
    matched_count = fields.Integer(
        string='Matched', compute='_compute_counts', store=True)
    unmatched_booked_count = fields.Integer(
        string='Unmatched (Booked)', compute='_compute_counts', store=True)
    unmatched_imported_count = fields.Integer(
        string='Unmatched (Imported)', compute='_compute_counts', store=True)

    # One2many to child records
    booked_line_ids = fields.One2many(
        comodel_name='tax.account.reconciliation.booked.line',
        inverse_name='reconciliation_id', string='Booked Transactions')
    imported_line_ids = fields.One2many(
        comodel_name='tax.account.reconciliation.imported.line',
        inverse_name='reconciliation_id', string='Imported Transactions')

    # Created settlement
    settlement_move_id = fields.Many2one(
        comodel_name='account.move', string='Settlement Entry',
        readonly=True)

    # API state (for OAuth2 flow)
    api_state = fields.Char(string='API State')

    # ------------------------------------------------------------------
    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.name = _('Tax Account Reconciliation %s → %s') % (
                    rec.date_from, rec.date_to)

    @api.depends('date_from', 'date_to', 'journal_id')
    def _compute_balances(self):
        for rec in self:
            if not rec.journal_id:
                continue
            tax_account = rec._get_tax_account()
            if not tax_account:
                rec.opening_balance = 0.0
                rec.closing_balance = 0.0
                continue
            # Opening balance: sum of all moves before date_from
            opening = sum(
                tax_account.with_context(
                    {'date_from': False, 'date_to': rec.date_from}
                ).balance,
                0.0 if isinstance(
                    tax_account.with_context(
                        {'date_from': False,
                         'date_to': rec.date_from}).balance,
                    bool) else 0.0)
            rec.opening_balance = opening
            # Closing balance: sum up to date_to
            closing = sum(
                tax_account.with_context(
                    {'date_from': False, 'date_to': rec.date_to}
                ).balance,
                0.0 if isinstance(
                    tax_account.with_context(
                        {'date_from': False,
                         'date_to': rec.date_to}).balance,
                    bool) else 0.0)
            rec.closing_balance = closing

    @api.depends('closing_balance', 'skv_balance')
    def _compute_balance_difference(self):
        for rec in self:
            rec.balance_difference = (
                (rec.closing_balance or 0.0)
                - (rec.skv_balance or 0.0))

    @api.depends('booked_line_ids.is_matched',
                 'imported_line_ids.is_matched')
    def _compute_counts(self):
        for rec in self:
            rec.matched_count = len(
                rec.booked_line_ids.filtered('is_matched'))
            rec.unmatched_booked_count = len(
                rec.booked_line_ids.filtered(
                    lambda l: not l.is_matched))
            rec.unmatched_imported_count = len(
                rec.imported_line_ids.filtered(
                    lambda l: not l.is_matched))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_tax_account(self):
        """Return account 1630 (Skattekonto) for the company."""
        self.ensure_one()
        return self.env['account.account'].search([
            ('company_ids', 'in', [self.company_id.id]),
            ('code', '=', '1630'),
        ], limit=1)

    def _build_tax_account_url(self):
        """Build the Skatteverket Tax Account transactions URL."""
        journal = self.journal_id
        account_number = (
            journal.bank_account_id.acc_number
            if journal.bank_account_id else '')
        if not account_number:
            raise UserError(_(
                "The tax journal must have a bank account "
                "with the tax account number (OCR)."))
        company = self.company_id or self.env.company
        base = company._get_skv_api_url('/skattekonto/v2')
        if not base.endswith('/'):
            base += '/'
        url = '%sskattekonton/%s/transaktioner' % (base, account_number)
        if self.date_from:
            url += '?datumFrom=%s' % self.date_from
        return url

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_open(self):
        """Move from draft → open: load booked lines."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_(
                "Reconciliation must be in draft state to open."))
        self._load_booked_lines()
        self.state = 'open'

    def action_fetch_transactions(self):
        """Fetch tax account transactions from Skatteverket API."""
        self.ensure_one()
        company = self.company_id or self.env.company
        access_token = self._get_skv_access_token(company)

        url = self._build_tax_account_url()
        headers = self._build_skv_headers(access_token)
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self._import_transactions(data)
                self.journal_id.write({
                    'tax_account_last_sync': fields.Datetime.now(),
                })
            else:
                _logger.error(
                    "SKV fetch error: %s %s",
                    response.status_code, response.text)
                raise UserError(_(
                    "Skatteverket API returned error %s:\n%s")
                    % (response.status_code, response.text[:500]))
        except requests.exceptions.RequestException as e:
            raise UserError(_(
                "Could not connect to Skatteverket API:\n%s") % str(e))

    def _load_booked_lines(self):
        """Load booked journal entries on account 1630 for the period."""
        self.booked_line_ids.unlink()
        tax_account = self._get_tax_account()
        if not tax_account:
            return

        domain = [
            ('account_id', '=', tax_account.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        move_lines = self.env['account.move.line'].search(
            domain, order='date asc, id asc')

        lines = []
        for ml in move_lines:
            lines.append((0, 0, {
                'move_line_id': ml.id,
                'date': ml.date,
                'name': ml.name or ml.ref or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'amount': ml.balance,
            }))
        if lines:
            self.write({'booked_line_ids': lines})

    def _import_transactions(self, data):
        """Import transactions from Skatteverket API response."""
        self.imported_line_ids.unlink()
        transactions = data.get('tidigareTransaktioner', [])
        if not transactions:
            raise UserError(_(
                "No transactions found in Skatteverket response."))

        lines = []
        for txn in transactions:
            amount = txn.get('beloppSkatteverket')
            if amount is None:
                amount = txn.get('beloppKronofogden', 0.0)
            lines.append((0, 0, {
                'skv_transaction_id': txn.get(
                    'transaktionsidentitet', ''),
                'date': txn.get('transaktionsdatum'),
                'name': txn.get('transaktionstext', ''),
                'amount': amount,
            }))
        if lines:
            self.write({'imported_line_ids': lines})

    def action_auto_match(self):
        """Auto-match booked and imported lines by amount ± tolerance."""
        self.ensure_one()
        tolerance_days = (
            self.company_id.skv_match_tolerance_days or 3)

        imported_lines = self.imported_line_ids.filtered(
            lambda l: not l.is_matched)
        booked_lines = self.booked_line_ids.filtered(
            lambda l: not l.is_matched)

        for imp in imported_lines:
            for booked in booked_lines:
                if booked.is_matched:
                    continue
                # Match on amount
                if round(imp.amount, 2) != round(booked.amount, 2):
                    continue
                # Check date tolerance
                if imp.date and booked.date:
                    diff = abs((imp.date - booked.date).days)
                    if diff <= tolerance_days:
                        booked.is_matched = True
                        imp.is_matched = True
                        booked.matched_imported_line_id = imp.id
                        imp.matched_booked_line_id = booked.id
                        break

    def action_manual_match(self, booked_line_ids, imported_line_id):
        """Manually match selected booked lines to one imported line."""
        self.ensure_one()
        imported_line = self.imported_line_ids.browse(imported_line_id)
        booked_lines = self.booked_line_ids.browse(booked_line_ids)
        if not imported_line or not booked_lines:
            raise UserError(_("Invalid selection for matching."))
        total_booked = sum(bl.amount for bl in booked_lines)
        if round(total_booked, 2) != round(imported_line.amount, 2):
            raise UserError(_(
                "Sum of selected booked lines (%s) does not match "
                "imported transaction amount (%s).")
                % (total_booked, imported_line.amount))
        for bl in booked_lines:
            bl.is_matched = True
            bl.matched_imported_line_id = imported_line.id
        imported_line.is_matched = True
        imported_line.matched_booked_line_id = booked_lines[0].id

    def action_create_settlement(self):
        """Create a settlement journal entry on the VAT journal.

        Posts the net difference between booked and SKV to adjust
        the tax account, similar to Business Central's
        "Calc. and Post VAT Settlement".
        """
        self.ensure_one()
        if self.settlement_move_id:
            raise UserError(_(
                "A settlement entry already exists for this "
                "reconciliation."))

        tax_account = self._get_tax_account()
        if not tax_account:
            raise UserError(_(
                "Account 1630 (Skattekonto) not found."))

        diff = self.balance_difference
        if round(diff, 2) == 0.0:
            # Already balanced — mark as done
            self.state = 'done'
            return

        journal = self.journal_id
        settlement_account = (
            journal.default_credit_account_id
            or journal.default_debit_account_id)

        if not settlement_account:
            raise UserError(_(
                "The VAT journal must have a default credit/debit "
                "account configured."))

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': _('Tax Account Settlement — %s') % self.name,
        })
        move_lines = [
            (0, 0, {
                'name': _('Skattekonto adjustment'),
                'account_id': tax_account.id,
                'debit': abs(diff) if diff < 0 else 0.0,
                'credit': diff if diff > 0 else 0.0,
                'move_id': move.id,
            }),
            (0, 0, {
                'name': _('Settlement counterpart'),
                'account_id': settlement_account.id,
                'debit': diff if diff > 0 else 0.0,
                'credit': abs(diff) if diff < 0 else 0.0,
                'move_id': move.id,
            }),
        ]
        move.write({'line_ids': move_lines})
        move.action_post()
        self.settlement_move_id = move.id
        self.state = 'done'

    def action_mass_reconcile(self):
        """Batch-reconcile past periods (like Fortnox 'Massavstämning').

        Marks all unmatched booked lines in prior periods as reconciled.
        """
        self.ensure_one()
        unmatched = self.booked_line_ids.filtered(
            lambda l: not l.is_matched)
        for line in unmatched:
            line.is_matched = True
        self.state = 'done'

    def action_verify_balance(self):
        """Compare account 1630 balance with SKV balance.

        Like Visma's final step: 'Jämför saldot på konto 1630
        med saldot på ditt skattekonto'.
        """
        self.ensure_one()
        tax_account = self._get_tax_account()
        if not tax_account:
            raise UserError(_("Account 1630 not found."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Balance Verification'),
                'message': _(
                    'Account 1630: %(booked)s\n'
                    'SKV Balance: %(skv)s\n'
                    'Difference: %(diff)s'
                ) % {
                    'booked': self.closing_balance,
                    'skv': self.skv_balance or 0.0,
                    'diff': self.balance_difference,
                },
                'type': 'warning' if self.balance_difference else 'success',
                'sticky': True,
            },
        }


# ---------------------------------------------------------------------------
# Booked Transaction Line
# ---------------------------------------------------------------------------


class TaxAccountReconciliationBookedLine(models.Model):
    _name = 'tax.account.reconciliation.booked.line'
    _description = 'Tax Account Reconciliation — Booked Line'
    _order = 'date asc, id asc'

    reconciliation_id = fields.Many2one(
        comodel_name='tax.account.reconciliation',
        string='Reconciliation', required=True, ondelete='cascade')
    move_line_id = fields.Many2one(
        comodel_name='account.move.line', string='Journal Item',
        readonly=True)
    date = fields.Date(string='Date', readonly=True)
    name = fields.Char(string='Description', readonly=True)
    debit = fields.Monetary(string='Debit', readonly=True)
    credit = fields.Monetary(string='Credit', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one(
        related='reconciliation_id.currency_id')

    is_matched = fields.Boolean(string='Matched', default=False)
    matched_imported_line_id = fields.Many2one(
        comodel_name='tax.account.reconciliation.imported.line',
        string='Matched With', readonly=True)
    comment = fields.Char(string='Comment')


# ---------------------------------------------------------------------------
# Imported (SKV) Transaction Line
# ---------------------------------------------------------------------------


class TaxAccountReconciliationImportedLine(models.Model):
    _name = 'tax.account.reconciliation.imported.line'
    _description = 'Tax Account Reconciliation — Imported Line'
    _order = 'date asc, id asc'

    reconciliation_id = fields.Many2one(
        comodel_name='tax.account.reconciliation',
        string='Reconciliation', required=True, ondelete='cascade')
    skv_transaction_id = fields.Char(
        string='SKV Transaction ID', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    name = fields.Char(string='Description', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one(
        related='reconciliation_id.currency_id')

    is_matched = fields.Boolean(string='Matched', default=False)
    matched_booked_line_id = fields.Many2one(
        comodel_name='tax.account.reconciliation.booked.line',
        string='Matched With', readonly=True)
    comment = fields.Char(string='Comment')
