from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag')
    rotrut_percent = fields.Float(string='Rot/Rut procent')
    rotrut_amount = fields.Monetary(compute='_compute_amount')


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'is_rotrut',
        'rotrut_percent'
        )
    def _compute_amount(self):
        super()._compute_amount()
        self.rotrut_amount = self.amount_total
        for move in self:
            if move.is_rotrut:
                if move.rotrut_percent > 0:
                    move.rotrut_amount = -abs(self.amount_total * self.rotrut_percent / 100)
                    move.amount_total += move.rotrut_amount
                    move.amount_total_signed += move.rotrut_amount
                    move.amount_residual = move.amount_total
                    move.amount_residual_signed = move.amount_total
