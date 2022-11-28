from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag')
    #rotrut_percent = fields.Float(string='Rot/Rut procent')
    rotrut_percent = fields.Float(store=True)
    rotrut_amount = fields.Monetary(string="Rot/Rut avdrag", compute='_compute_amount')


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
        self.rotrut_amount = 0
        line = None
        for move in self:

            for line in move.line_ids:
                if line.rotrut_id:
                    move.rotrut_amount += line.price_subtotal

            if line:
                for tax in line.tax_ids:
                    move.rotrut_amount *= 1 + (tax.amount / 100)

            if move.is_rotrut:
                if move.rotrut_percent > 0:
                    move.rotrut_amount = -abs(move.rotrut_amount * self.rotrut_percent / 100)
                    move.amount_total += move.rotrut_amount
                    move.amount_total_signed += move.rotrut_amount
                    move.amount_residual = move.amount_total
                    move.amount_residual_signed = move.amount_total
