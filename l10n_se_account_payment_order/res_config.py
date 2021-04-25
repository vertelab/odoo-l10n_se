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


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_account_ids = fields.Many2many(comodel_name='account.account', relation='payment_account', string='Payment Accounts', help='Accounts should include in payment')
    nix_payment_account_ids = fields.Many2many(comodel_name='account.account', relation='nix_payment_account', string='Payment Accounts Nix', help='Accounts should not include in payment')

    def set_account_payment_order(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('l10n_se_account_payment_order.payment_account_ids', self.payment_account_ids.mapped('id'))
        conf.set_param('l10n_se_account_payment_order.nix_payment_account_ids', self.nix_payment_account_ids.mapped('id'))


    @api.model
    def get_default_account_payment_order(self, fields):
        conf = self.env['ir.config_parameter']
        payment_account_ids = conf.get_param('l10n_se_account_payment_order.payment_account_ids')
        nix_payment_account_ids = conf.get_param('l10n_se_account_payment_order.nix_payment_account_ids')
        return {
            'payment_account_ids': eval(payment_account_ids) if payment_account_ids else [],
            'nix_payment_account_ids': eval(nix_payment_account_ids) if nix_payment_account_ids else [],
        }


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = 'account.payment.line.create'

    def _prepare_move_line_domain(self):
        conf = self.env['ir.config_parameter']
        res = super(AccountPaymentLineCreate, self)._prepare_move_line_domain()
        payment_account_ids = conf.get_param('l10n_se_account_payment_order.payment_account_ids')
        nix_payment_account_ids = conf.get_param('l10n_se_account_payment_order.nix_payment_account_ids')
        if nix_payment_account_ids:
            # add accounts should not include in payment
            res += [('account_id', 'not in', eval(nix_payment_account_ids))]
        if payment_account_ids:
            for e in res:
                # add specified accounts which are not defined as internal_type: payable
                if e[0] == 'account_id.internal_type':
                    internal_type_domain = e
                    res.remove(e)
                    res += ['|', internal_type_domain, ('account_id', 'in', eval(payment_account_ids))]
                    break
        return res
