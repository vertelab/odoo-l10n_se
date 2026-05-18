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

    @api.model
    def _amounts_match(self, stmt_amount, move_residual, tolerance=0.01):
        """Compare absolute amounts within a small floating-point tolerance."""
        return abs(abs(stmt_amount) - abs(move_residual)) <= tolerance
