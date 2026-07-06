# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    def generate_move(self):
        """
        Override original method. create seperated move for each partner bank
        """
        self.ensure_one()
        am_obj = self.env['account.move']
        post_move = self.payment_mode_id.post_move
        trfmoves = {}
        for bline in self.bank_line_ids:
            hashcode = bline.move_line_offsetting_account_hashcode()
            if hashcode in trfmoves:
                trfmoves[hashcode] += bline
            else:
                trfmoves[hashcode] = bline
        for hashcode, blines in trfmoves.items():
            for bline in blines:
                mvals = self._prepare_move(bline)
                move = am_obj.create(mvals)
                if self.payment_mode_id.post_move:
                    if post_move:
                        move.post()
                    bline.reconcile_payment_lines()


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = 'account.payment.line.create'

    def _compute_move_line_domain(self):
        """Extend domain to include additional reconcilable account types.

        Swedish accounts like 1630 (Skattekonto) can have account_type
        'liability_current' or 'asset_current', neither of which is included
        in the standard domain (only 'liability_payable' and
        'asset_receivable').

        Also filter out lines with amount_residual = 0, which occur when
        non-reconcilable accounts (e.g. VAT accounts) match the domain via
        credit > 0 but have no actual residual to pay.
        """
        super()._compute_move_line_domain()
        if (
            self.order_id
            and self.order_id.payment_type == 'outbound'
            and self.move_line_domain
        ):
            new_domain = []
            for item in self.move_line_domain:
                if (
                    isinstance(item, tuple)
                    and item[0] == 'account_id.account_type'
                ):
                    new_domain.append(
                        ('account_id.account_type', 'in', [
                            'liability_payable',
                            'asset_receivable',
                            'liability_current',
                            'asset_current',
                        ])
                    )
                else:
                    new_domain.append(item)
            new_domain.append(("amount_residual", "!=", 0.0))
            self.move_line_domain = new_domain
