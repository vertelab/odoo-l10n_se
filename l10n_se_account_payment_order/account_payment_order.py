# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018- Vertel (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval

import logging
_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.multi
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
        for hashcode, blines in trfmoves.iteritems():
            for bline in blines:
                # create sperate move to each bank payment line
                mvals = self._prepare_move(bline)
                total_company_currency = total_payment_currency = 0
                total_company_currency += bline.amount_company_currency
                total_payment_currency += bline.amount_currency
                partner_ml_vals = self._prepare_move_line_partner_account(bline)
                mvals['line_ids'].append((0, 0, partner_ml_vals))
                trf_ml_vals = self._prepare_move_line_offsetting_account(total_company_currency, total_payment_currency, bline)
                mvals['line_ids'].append((0, 0, trf_ml_vals))
                move = am_obj.create(mvals)
                bline.reconcile_payment_lines()
                if post_move:
                    move.post()
