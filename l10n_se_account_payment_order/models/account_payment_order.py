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
                    
                    res += ['|','|', internal_type_domain, ('account_id.id', 'in', type_list),('account_id.user_type_id.type','in',account_list)]
                    #
                    break
        _logger.warning(f"jakmar: domain {res}")
        return res
        
#Model used to save settings for the Account Payment Domain
class AccountPaymentConfig(models.Model):
        _name = 'account.payment.config'
        # ~ allowed_account_type_ids = fields.One2many(comodel_name='account.account.type', string='Allowed Account Types', help='Accounts that belong to these types show up', inverse_name='account_payment_config')
        # ~ disallowed_account_ids = fields.One2many(comodel_name='account.account', string='Disallowed Accounts', help='These Accounts will not show up', inverse_name='account_payment_config')
        _rec_name = 'config_name'
        config_name = fields.Char()
        
        allowed_account_type_ids = fields.Many2many(comodel_name='account.account.type', string='Allowed Account Types', help='Accounts that belong to these types show up',
        domain="[('type', 'in', ('receivable', 'payable'))]")
        
        allowed_account_ids = fields.Many2many(comodel_name='account.account', string='Disallowed Accounts', help='These Accounts will not show up',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable'))]")
        
# ~ class AccountAccount(models.Model):
        # ~ _inherit = 'account.account'
        # ~ account_payment_config = fields.Many2one(comodel_name = "account.payment.config", string = "Account Payment Config")
        
# ~ class AccountAccountType(models.Model):
        # ~ _inherit = 'account.account.type'
        # ~ account_payment_config = fields.Many2one(comodel_name = "account.payment.config", string = "Account Payment Config")
