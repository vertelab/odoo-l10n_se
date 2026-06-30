import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_matching_suggestions(self, st_lines, partner_id=None):
        """Extend OCA matching suggestions to include OCR-based matching.

        When a bank statement line has an *extracted_ocr*, search for
        unpaid customer invoices whose *ocr_number* matches and return
        them as a 100% matching suggestion.
        """
        suggestions = super()._get_matching_suggestions(
            st_lines, partner_id=partner_id,
        )
        ocr_lines = st_lines.filtered('extracted_ocr')
        if not ocr_lines:
            return suggestions

        ocr_moves = self._find_moves_by_ocr(ocr_lines)
        for line in ocr_lines:
            moves = ocr_moves.get(line.id, self.env['account.move'])
            if moves:
                suggestions[line.id].extend([
                    {
                        'type': 'invoice',
                        'id': move.id,
                        'name': move.name,
                        'amount': move.amount_residual,
                        'date': move.invoice_date or move.date,
                        'account_id': move.line_ids.filtered(
                            lambda l: l.account_id.account_type
                            in ('asset_receivable', 'liability_payable')
                        ).mapped('account_id')[:1].id,
                        'partner_id': move.partner_id.id,
                        'match_percentage': 100.0,
                        'source': 'ocr_match',
                    }
                    for move in moves
                ])
        return suggestions

    @api.model
    def _find_moves_by_ocr(self, st_lines):
        """Return a dict mapping statement-line id to matching account.moves
        whose *ocr_number* equals the line's *extracted_ocr* and whose
        payment_state indicates the invoice is still open.
        """
        result = {}
        for line in st_lines:
            if not line.extracted_ocr:
                continue
            moves = self.env['account.move'].search([
                ('ocr_number', '=', line.extracted_ocr),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('company_id', '=', line.company_id.id),
            ])
            if moves:
                result[line.id] = moves
                _logger.info(
                    'OCR match: line %s -> invoice(s) %s',
                    line.id, moves.ids,
                )
        return result


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def _get_reconcile_model_lines(self):
        """Inject OCR-extracted reference into the data consumed by the
        OCA reconciliation widget so that text-based rules can also fire."""
        result = super()._get_reconcile_model_lines()
        for line in self:
            if line.extracted_ocr:
                line_vals = result.get(line.id, {})
                line_vals['transaction_ref'] = line.extracted_ocr
                result[line.id] = line_vals
        return result

    def _try_auto_reconcile(self):
        """Override auto-reconcile to also attempt an OCR-based match
        before falling back to the standard logic.

        If *extracted_ocr* matches exactly one unpaid invoice with the
        same amount residual, reconcile immediately.
        """
        reconciled = self.env['account.bank.statement.line']
        for line in self:
            if line.extracted_ocr and not line.is_reconciled:
                moves = self.env['account.move'].search([
                    ('ocr_number', '=', line.extracted_ocr),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('company_id', '=', line.company_id.id),
                ])
                if len(moves) == 1:
                    move = moves[0]
                    residual = move.amount_residual
                    if self._amounts_match(line.amount, residual):
                        line.reconcile({'move_id': move.id})
                        reconciled |= line
                        _logger.info(
                            'Auto-reconciled line %s with invoice %s via OCR %s',
                            line.id, move.name, line.extracted_ocr,
                        )
                        continue
        remainder = self - reconciled
        if remainder:
            reconciled |= super(
                AccountBankStatementLine, remainder,
            )._try_auto_reconcile()
        return reconciled

    # ------------------------------------------------------------------
    # 4-pass greedy matching algorithm
    # Inspired by Accounted (erp-mafia/accounted)
    # ------------------------------------------------------------------

    def _try_4pass_auto_reconcile(self):
        """Run 4-pass greedy matching on this statement's unreconciled lines.

        Passes (ordered by confidence):
          1. Exact amount + exact date                        (95%)
          2. Exact amount + OCR/reference within ±90 days     (90%)
          3. Exact amount + date within ±3 days               (85%)
          4. Fuzzy amount (±0.01) + exact date                (75%)

        Uses greedy matching: each GL line can only be matched once.
        Returns the set of reconciled statement lines.
        """
        self.ensure_one()

        unreconciled = self.line_ids.filtered(
            lambda l: not l.is_reconciled and l.amount != 0
        )
        if not unreconciled:
            return self.env['account.bank.statement.line']

        # Collect all open move lines on bank accounts (1930, 1931, etc.)
        bank_accounts = self.env['account.account'].search([
            ('code', 'in', ['1930', '1931', '1932', '1933']),
            ('company_id', '=', self.company_id.id),
        ])
        if not bank_accounts:
            return self.env['account.bank.statement.line']

        # Fetch unmatched move lines on bank accounts within date range
        date_from = min(unreconciled.mapped('date'))
        date_to = max(unreconciled.mapped('date'))

        move_lines = self.env['account.move.line'].search([
            ('account_id', 'in', bank_accounts.ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', self.company_id.id),
        ])
        if not move_lines:
            return self.env['account.bank.statement.line']

        # Build candidates with confidence scores
        candidates = []
        for line in unreconciled:
            for ml in move_lines:
                match = self._classify_match(line, ml)
                if match:
                    candidates.append(match)

        # Sort by confidence descending
        candidates.sort(key=lambda m: m['confidence'], reverse=True)

        # Greedy: match each GL line at most once
        matched_gl_lines = set()
        reconciled_lines = self.env['account.bank.statement.line']

        for candidate in candidates:
            st_line = candidate['statement_line']
            gl_line = candidate['move_line']

            if st_line.is_reconciled:
                continue
            if gl_line.id in matched_gl_lines:
                continue

            try:
                # Find the move that this GL line belongs to
                move = gl_line.move_id
                st_line.reconcile({'move_id': move.id})
                reconciled_lines |= st_line
                matched_gl_lines.add(gl_line.id)
                _logger.info(
                    '4-pass auto-reconciled st_line %s with move %s (method=%s, confidence=%.0f%%)',
                    st_line.id, move.name, candidate['method'], candidate['confidence'] * 100,
                )
            except Exception:
                _logger.debug('Failed to reconcile st_line %s', st_line.id)

        return reconciled_lines

    @api.model
    def _classify_match(self, st_line, gl_line):
        """Classify a potential match between a statement line and a GL line.

        Returns a dict with match metadata, or None if no match.
        """
        stmt_amount = abs(st_line.amount)
        gl_amount = abs(gl_line.debit - gl_line.credit)
        stmt_date = st_line.date
        gl_date = gl_line.date

        amount_exact = abs(stmt_amount - gl_amount) < 0.005
        amount_fuzzy = abs(stmt_amount - gl_amount) <= 0.01
        date_exact = stmt_date == gl_date
        date_within_3 = abs((stmt_date - gl_date).days) <= 3
        date_within_90 = abs((stmt_date - gl_date).days) <= 90
        has_ocr = bool(st_line.extracted_ocr) and bool(
            gl_line.move_id.ocr_number == st_line.extracted_ocr
        )

        match = None

        # Pass 1: Exact amount + exact date
        if amount_exact and date_exact:
            match = {'method': 'auto_exact', 'confidence': 0.95}

        # Pass 2: Exact amount + OCR reference within ±90 days
        elif amount_exact and has_ocr and date_within_90:
            match = {'method': 'auto_reference', 'confidence': 0.90}

        # Pass 3: Exact amount + date within ±3 days
        elif amount_exact and date_within_3:
            match = {'method': 'auto_date_range', 'confidence': 0.85}

        # Pass 4: Fuzzy amount (±0.01) + exact date
        elif amount_fuzzy and date_exact:
            match = {'method': 'auto_fuzzy', 'confidence': 0.75}

        if match:
            match.update({
                'statement_line': st_line,
                'move_line': gl_line,
            })
            return match
        return None

    @api.model
    def _amounts_match(self, stmt_amount, move_residual, tolerance=0.01):
        """Compare absolute amounts within a small floating-point tolerance."""
        return abs(abs(stmt_amount) - abs(move_residual)) <= tolerance


class AccountBankStatement(models.Model):
    """Add 4-pass auto-reconciliation batch action to bank statements."""

    _inherit = 'account.bank.statement'

    def action_4pass_reconcile(self):
        """Run 4-pass greedy matching on all statements in this recordset.

        Can be triggered from a button on the bank statement form or
        from a cron job for fully automated reconciliation.
        """
        total_reconciled = 0
        for statement in self:
            if statement.state != 'posted':
                continue
            reconciled = statement._try_4pass_auto_reconcile()
            total_reconciled += len(reconciled)

        if total_reconciled:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('4-Pass Reconciliation'),
                    'message': _('%d transaction(s) auto-reconciled.') % total_reconciled,
                    'type': 'success',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('4-Pass Reconciliation'),
                'message': _('No new matches found.'),
                'type': 'info',
                'sticky': False,
            },
        }
