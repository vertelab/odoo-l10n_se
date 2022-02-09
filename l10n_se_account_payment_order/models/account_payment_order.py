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
                # create sperate move to each bank payment line
                mvals = self._prepare_move(bline) 
                total_company_currency = total_payment_currency = 0
                total_company_currency += bline.amount_company_currency
                total_payment_currency += bline.amount_currency
                
                # ~ partner_ml_vals = self._prepare_move_line_partner_account(bline) ## ADDS DUPLICATE LINES?
                # ~ mvals['line_ids'].append((0, 0, partner_ml_vals))

                # ~ trf_ml_vals = self._prepare_move_line_offsetting_account(total_company_currency, total_payment_currency, bline)
                # ~ mvals['line_ids'].append((0, 0, trf_ml_vals))

                move = am_obj.create(mvals)
                _logger.warning(f"move = {move}")

                _logger.warning(f"lines = {move.line_ids}")
                if post_move:
                    move.post()
                bline.reconcile_payment_lines()
                
                    
# ~ class BankPaymentLine(models.Model):
    # ~ _inherit = "bank.payment.line"
    
    # ~ """
    # ~ Override original method. To be able to handle a move for each partner bank
    # ~ """    
    # ~ def reconcile(self):
        # ~ self.ensure_one()
        # ~ amlo = self.env["account.move.line"]
        # ~ transit_mlines = amlo.search([("bank_payment_line_id", "=", self.id)])
        # ~ for line in transit_mlines:
            # ~ _logger.warning(f"{line.read()}")
        # ~ _logger.warning(f"{transit_mlines=}")
        # ~ assert len(transit_mlines) == 1, "We should have only 1 move"
        # ~ for move_line in transit_mlines:
            # ~ transit_mline = transit_mlines[0]
            # ~ assert not transit_mline.reconciled, "Transit move should not be reconciled"
            
            # ~ lines_to_rec = transit_mline
            # ~ for payment_line in self.payment_line_ids:

                # ~ if not payment_line.move_line_id:
                    # ~ raise UserError(
                        # ~ _(
                            # ~ "Can not reconcile: no move line for "
                            # ~ "payment line %s of partner '%s'."
                        # ~ )
                        # ~ % (payment_line.name, payment_line.partner_id.name)
                    # ~ )
                # ~ if payment_line.move_line_id.reconciled:
                    # ~ raise UserError(
                        # ~ _("Move line '%s' of partner '%s' has already " "been reconciled")
                        # ~ % (payment_line.move_line_id.name, payment_line.partner_id.name)
                    # ~ )
                # ~ if payment_line.move_line_id.account_id != transit_mline.account_id:
                    # ~ raise UserError(
                        # ~ _(
                            # ~ "For partner '%s', the account of the account "
                            # ~ "move line to pay (%s) is different from the "
                            # ~ "account of of the transit move line (%s)."
                        # ~ )
                        # ~ % (
                            # ~ payment_line.move_line_id.partner_id.name,
                            # ~ payment_line.move_line_id.account_id.code,
                            # ~ transit_mline.account_id.code,
                        # ~ )
                    # ~ )

                # ~ lines_to_rec += payment_line.move_line_id

            # ~ lines_to_rec.reconcile()

class AccountPaymentLineCreate(models.TransientModel):
    _inherit = 'account.payment.line.create'

    def _prepare_move_line_domain(self):
        conf = self.env["account.payment.config"].search([])
        res = super(AccountPaymentLineCreate, self)._prepare_move_line_domain()
        if conf.allowed_account_type_ids or conf.allowed_account_ids:
            for e in res:
                # add specified accounts which are not defined as internal_type: payable
                if e[0] == 'account_id.internal_type':
                    internal_type_domain = e
                    res.remove(e)
                    if conf.allowed_account_type_ids:
                        type_list = conf.allowed_account_type_ids.mapped('id')
                    else:
                        type_list = []
                    if conf.allowed_account_ids:
                        account_list = conf.allowed_account_ids.mapped('id')
                    else:
                        account_list = []
                    
                    res += ['|' ,('account_id.id', 'in', account_list),('account_id.user_type_id','in',type_list)]
                    #
                    break
        # ~ _logger.warning(f"jakmar: domain {res}")
        return res
        
#Model used to save settings for the Account Payment Domain
class AccountPaymentConfig(models.Model):
        _name = 'account.payment.config'
        # ~ allowed_account_type_ids = fields.One2many(comodel_name='account.account.type', string='Allowed Account Types', help='Accounts that belong to these types show up', inverse_name='account_payment_config')
        # ~ disallowed_account_ids = fields.One2many(comodel_name='account.account', string='Disallowed Accounts', help='These Accounts will not show up', inverse_name='account_payment_config')
        _rec_name = 'config_name'
        config_name = fields.Char()
        
        allowed_account_type_ids = fields.Many2many(comodel_name='account.account.type',  string='Allowed Account Types', help='Accounts that belong to these types show up',
        domain="[('type', 'in', ('receivable', 'payable'))]")
        
        allowed_account_ids = fields.Many2many(comodel_name='account.account', string='Allowed Accounts', help='These Accounts will show up',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable'))]")
        

