"""Account demo: load journal entries quarter by quarter.

The data is split into one JSON file per quarter (2024Q1..2027Q4). Each
file holds the moves for that quarter only. Loading is driven by
demo.dataset, which owns the sequence rule — this module only knows how
to turn a quarter's JSON into account.move records.
"""
import gzip
import json
import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

LOADER_VERSION = 'v10-rounding-in-generator'

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'datasets')


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    @api.model
    def _account_demo_company(self):
        """The demo company — the one whose chart we load into."""
        return self.env.ref('l10n_se_demo_company.company')

    @api.model
    def _account_demo_account_by_code(self, code):
        """Find an l10n_se account by BAS code for the demo company.

        The chart template stores codes in code_store keyed by chart
        version. se_K2 uses key "3" (se uses "1", generic_coa uses "1"
        as well). Searching on the ORM `code` field returns nothing for
        se_K2 accounts, so the lookup goes through code_store across all
        keys present.
        """
        if not code:
            return False
        company = self._account_demo_company()
        code = self.CODE_OVERRIDE.get(code, code)
        self.env.cr.execute("""
            SELECT aa.id
              FROM account_account aa
              JOIN account_account_res_company_rel rel
                ON rel.account_account_id = aa.id
             WHERE rel.res_company_id = %s
               AND EXISTS (
                   SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                    WHERE kv.v = %s)
             LIMIT 1
        """, (company.id, code))
        row = self.env.cr.fetchone()
        if row:
            return row[0]
        # Not in the chart: fall back to the nearest parent BAS account.
        # SFA has industry-specific accounts (3011, 4011, 5614...) that the
        # standard K2 chart does not carry. Walking up the code keeps the
        # move balanced and the account class correct.
        for fallback in self._account_demo_fallback_codes(code):
            self.env.cr.execute("""
                SELECT aa.id
                  FROM account_account aa
                  JOIN account_account_res_company_rel rel
                    ON rel.account_account_id = aa.id
                 WHERE rel.res_company_id = %s
                   AND EXISTS (
                       SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                        WHERE kv.v = %s)
                 LIMIT 1
            """, (company.id, fallback))
            row = self.env.cr.fetchone()
            if row:
                return row[0]
        return False

    # Codes that have no counterpart in se_K2 at all. 8710/8750 are
    # resultatdisposition (year-end), which belongs to the closing flow,
    # not to running bookkeeping — map them to the tax allocation reserve
    # accounts so the move stays balanced and in the right class.
    CODE_OVERRIDE = {  # noqa: RUF012 - Odoo class attribute
        '8710': '8811',
        '8750': '8819',
    }

    @staticmethod
    def _account_demo_fallback_codes(code):
        """Candidate parent codes, most specific first.

        3011 -> 3010 -> 3000 -> 3001
        5614 -> 5610 -> 5600 -> 5611
        """
        if len(code) != 4 or not code.isdigit():
            return []
        candidates = [
            code[:3] + '0',      # 3011 -> 3010
            code[:2] + '00',     # 3010 -> 3000
            code[:1] + '000',    # 3000 -> 3000 (same)
        ]
        # Common chart members inside the same group
        group = code[:2]
        candidates += [f'{group}01', f'{group}02', f'{group}11']
        seen, out = set(), []
        for c in candidates:
            if c != code and c not in seen:
                seen.add(c)
                out.append(c)
        return out

    @api.model
    def _account_demo_tax_by_name(self, name):
        """Find a company tax by its name fragment."""
        if not name:
            return False
        tax = self.env['account.tax'].search([
            ('name', 'ilike', name),
            ('company_id', '=', self._account_demo_company().id),
        ], limit=1)
        return tax.id if tax else False

    @api.model
    def _account_demo_partner_by_ref(self, ref):
        """Resolve a DEMO-<id> reference to a demo partner."""
        if not ref:
            return False
        partner = self.env['res.partner'].search([('ref', '=', ref)], limit=1)
        return partner.id if partner else False

    # ------------------------------------------------------------------
    # Loading one quarter
    # ------------------------------------------------------------------

    @api.model
    def _account_demo_load_quarter(self, dataset):
        """Load the moves for one demo.dataset row. Returns the count."""
        path = os.path.join(DATA_DIR, f"{dataset.name.lower()}.json.gz")
        if not os.path.exists(path):
            _logger.warning('account_demo: no data file for %s (%s)',
                            dataset.name, path)
            return 0
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            moves = json.load(f)
        _logger.warning('account_demo: LOADER %s loading %s (%s moves)',
                        LOADER_VERSION, dataset.name, len(moves))

        count = 0
        skipped = 0
        for move_data in moves:
            vals = self._account_demo_prepare_move(move_data)
            if not vals.get('journal_id'):
                _logger.warning(
                    'account_demo: skipping %s, journal not resolved',
                    move_data.get('name'))
                continue
            # Reject unbalanced moves instead of writing them. The loader
            # runs with check_move_validity=False for speed, which would
            # otherwise let a broken source row through.
            net = sum((v[2].get('debit') or 0) - (v[2].get('credit') or 0)
                      for v in vals['line_ids'])
            if abs(net) > 0.01:
                _logger.warning(
                    'account_demo: skipping unbalanced move %s (net %.2f, '
                    '%s lines)', vals.get('name'), net, len(vals['line_ids']))
                skipped += 1
                continue
            if (vals['move_type'] in ('out_invoice', 'in_invoice',
                                      'out_refund', 'in_refund')
                    and not vals.get('partner_id')):
                # Odoo requires a partner on invoices and refunds. Nine SFA
                # credit notes carry none on any line; they cannot be posted.
                _logger.info(
                    'account_demo: skipping %s without partner',
                    vals.get('name'))
                skipped += 1
                continue
            if not vals['line_ids']:
                # A move where every line has a zero amount cannot be
                # posted. SFA has 34 such leftovers; they carry nothing.
                _logger.info(
                    'account_demo: skipping empty move %s', vals.get('name'))
                skipped += 1
                continue
            move = self.with_context(check_move_validity=False).create(vals)
            for ml in move.line_ids:
                if ml.display_type == 'product':
                    tax_ids = move.line_ids.filtered(
                        lambda l: l.display_type == 'tax' and l.tax_line_id
                    ).mapped('tax_line_id').ids
                    if tax_ids:
                        ml.write({'tax_ids': [(6, 0, tax_ids)]})
            # The demo data must be posted: a draft entry is invisible to
            # every report — balance sheet, P&L, VAT, aged lists.
            move.action_post()
            count += 1
        _logger.info('account_demo: %s loaded, %s moves, %s skipped',
                     dataset.name, count, skipped)
        return count

    @api.model
    def _account_demo_first_line_partner(self, move_data):
        """The partner of the first line that has one.

        SFA leaves the partner empty on some credit notes; the receivable
        or payable line still carries it, and Odoo requires a partner on
        invoices and refunds.
        """
        for line in move_data.get('line_ids', []):
            if line.get('partner_ref'):
                return self._account_demo_partner_by_ref(line['partner_ref'])
        return False

    @api.model
    def _account_demo_prepare_move(self, move_data):
        journal = self.env['account.journal'].search([
            ('code', '=', move_data.get('journal_code')),
            ('company_id', '=', self._account_demo_company().id),
        ], limit=1)
        vals = {
            'name': move_data.get('name'),
            'date': move_data.get('date'),
            'move_type': move_data.get('move_type'),
            'journal_id': journal.id if journal else False,
            'company_id': self._account_demo_company().id,
            'partner_id': (self._account_demo_partner_by_ref(
                move_data.get('partner_ref'))
                or self._account_demo_first_line_partner(move_data)),
            'currency_id': self.env.ref('base.SEK').id,
            'invoice_date': move_data.get('invoice_date'),
            'invoice_date_due': move_data.get('invoice_date_due'),
            'payment_reference': move_data.get('payment_reference'),
            'line_ids': [],
        }
        for line in move_data.get('line_ids', []):
            # Zero-amount lines carry nothing and break the balance when
            # Odoo merges or drops them. SFA has a few (empty payment_term
            # rows, line_note placeholders).
            if (abs(line.get('debit') or 0) < 0.005
                    and abs(line.get('credit') or 0) < 0.005):
                continue
            line_vals = {
                'sequence': line.get('sequence'),
                'date': move_data.get('date'),
                'date_maturity': line.get('date_maturity'),
                'account_id': self._account_demo_account_by_code(
                    line.get('account_code')),
                'partner_id': self._account_demo_partner_by_ref(
                    line.get('partner_ref')),
                'debit': line.get('debit') or 0,
                'credit': line.get('credit') or 0,
                'currency_id': self.env.ref('base.SEK').id,
                'tax_line_id': self._account_demo_tax_by_name(
                    line.get('tax_name')),
                # Only the display types Odoo knows are passed through.
                # SFA has 'rounding' and 'line_note' which the loader does
                # not reproduce — they become normal product lines so the
                # amount is not silently dropped.
                'display_type': (line.get('display_type')
                                 if line.get('display_type') in
                                 ('product', 'tax', 'payment_term',
                                  'line_section', 'line_note', 'cogs',
                                  'rounding')
                                 else 'product'),
                'journal_id': vals['journal_id'],
                'name': line.get('name'),
            }
            # On an invoice, _compute_balance resets balance to 0 and
            # recomputes it from price_unit * quantity. Without this the
            # product lines are written with 0,00 and the move unbalances.
            if (vals['move_type'] != 'entry'
                    and line_vals['display_type'] == 'product'):
                # price_unit is the line amount before tax. On a sale
                # document a credit line has a positive price_unit; Odoo
                # derives the sign from the move type. Passing the raw
                # balance would flip sale lines to debit.
                amount = (line.get('debit') or 0) - (line.get('credit') or 0)
                # Only out_invoice flips sign. A credit note (out_refund) and
                # everything on the purchase side keep the balance sign.
                if vals['move_type'] == 'out_invoice':
                    amount = -amount
                # A vendor credit note (in_refund) has debit lines on the
                # payable account; Odoo expects a negative price_unit there.
                if vals['move_type'] == 'in_refund':
                    amount = -amount
                line_vals['price_unit'] = amount
                line_vals['quantity'] = 1.0
            if not line_vals.get('date_maturity'):
                line_vals['date_maturity'] = (
                    move_data.get('invoice_date_due') or move_data.get('date'))
            acct_id = line_vals.get('account_id')
            if acct_id:
                account = self.env['account.account'].browse(acct_id)
                is_receivable = account.account_type in (
                    'asset_receivable', 'liability_payable')
                # Odoo's _check_payable_receivable: on a sale document every
                # asset_receivable line and nothing else must be
                # payment_term; on a purchase document every
                # liability_payable line and nothing else. SFA puts
                # payment_term on secondary accounts (2441, 2460) and
                # sometimes omits it on the primary one, so the flag is
                # recomputed from account_type and move type.
                if is_receivable and vals['move_type'] != 'entry':
                    line_vals['display_type'] = 'payment_term'
                    if not line_vals.get('date_maturity'):
                        line_vals['date_maturity'] = (
                            move_data.get('invoice_date_due')
                            or move_data.get('date'))
                elif is_receivable:
                    # Plain entries: a normal move line, no due date.
                    line_vals['display_type'] = 'product'
                    line_vals['date_maturity'] = False
                elif line_vals.get('display_type') == 'payment_term':
                    # payment_term on a non-receivable account is invalid
                    line_vals['display_type'] = 'product'
            vals['line_ids'].append((0, 0, line_vals))
        return vals

    @api.model
    def _account_demo_unload_quarter(self, dataset):
        """Remove every move dated inside the quarter. Returns the count."""
        year = dataset.year
        quarter = int(dataset.quarter)
        start = f'{year}-{(quarter - 1) * 3 + 1:02d}-01'
        if quarter == 4:
            end = f'{year + 1}-01-01'
        else:
            end = f'{year}-{quarter * 3 + 1:02d}-01'
        moves = self.search([
            ('date', '>=', start),
            ('date', '<', end),
            ('company_id', '=', self._account_demo_company().id),
        ])
        count = len(moves)
        if count:
            moves.with_context(force_delete=True).unlink()
        _logger.info('account_demo: unloaded %s, %s moves', dataset.name, count)
        return count

    @api.model
    def _account_demo_unreconcile_quarter(self, dataset):
        """Drop payments and reconciliation for the quarter.

        Order matters: full reconcile, then partial, then payments, then
        bank statement lines. account.payment refuses to unlink while its
        move is still reconciled.
        """
        year = dataset.year
        quarter = int(dataset.quarter)
        start = f'{year}-{(quarter - 1) * 3 + 1:02d}-01'
        end = (f'{year + 1}-01-01' if quarter == 4
               else f'{year}-{quarter * 3 + 1:02d}-01')
        domain = [
            ('date', '>=', start),
            ('date', '<', end),
            ('company_id', '=', self._account_demo_company().id),
        ]

        Full = self.env['account.full.reconcile']
        Partial = self.env['account.partial.reconcile']
        Payment = self.env['account.payment']
        BankLine = self.env['account.bank.statement.line']

        moves = self.search(domain)
        lines = moves.line_ids

        # 1. Full reconciliations touching these lines
        fulls = Full.search([
            '|',
            ('reconciled_line_ids', 'in', lines.ids),
            ('exchange_move_id', 'in', moves.ids),
        ])
        if fulls:
            fulls.unlink()

        # 2. Partial reconciliations
        partials = Partial.search([
            '|', ('debit_move_id', 'in', lines.ids),
            ('credit_move_id', 'in', lines.ids),
        ])
        if partials:
            partials.unlink()

        # 3. Payments in the quarter
        payments = Payment.search(domain)
        if payments:
            payments.with_context(force_delete=True).unlink()

        # 4. Bank statement lines in the quarter
        bank_lines = BankLine.search(domain)
        count = len(bank_lines)
        if bank_lines:
            bank_lines.with_context(force_delete=True).unlink()

        _logger.info(
            'account_demo: unreconciled %s — %s full, %s partial, %s payments, '
            '%s bank lines', dataset.name, len(fulls), len(partials),
            len(payments), count)
        return count
