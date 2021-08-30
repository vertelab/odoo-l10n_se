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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_account_ids = fields.Many2many(comodel_name='account.account', relation='payment_account', string='Payment Accounts', help='Accounts should include in payment')
    nix_payment_account_ids = fields.Many2many(comodel_name='account.account', relation='nix_payment_account', string='Payment Accounts Nix', help='Accounts should not include in payment')
    
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        if self.payment_account_ids.exists():
            self.env['ir.config_parameter'].sudo().set_param(
                'l10n_se_account_payment_order.payment_account_ids',
                ','.join([str(x) for x in self.payment_account_ids.ids]))
        else:
            self.env['ir.config_parameter'].sudo().set_param('l10n_se_account_payment_order.payment_account_ids', False)
        
        if self.nix_payment_account_ids.exists():
            self.env['ir.config_parameter'].sudo().set_param(
                'l10n_se_account_payment_order.nix_payment_account_ids',
                ','.join([str(x) for x in self.nix_payment_account_ids.ids]))
        else:
            self.env['ir.config_parameter'].sudo().set_param('l10n_se_account_payment_order.nix_payment_account_ids', False)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        payment_account_ids = [int(x) for x in params.get_param('l10n_se_account_payment_order.payment_account_ids', '').split(',') if x]
        if payment_account_ids:
            res.update(payment_account_ids = [(6 ,0 , payment_account_ids)])
            
        nix_payment_account_ids = [int(x) for x in params.get_param('l10n_se_account_payment_order.nix_payment_account_ids', '').split(',') if x]
        if nix_payment_account_ids:
            res.update(nix_payment_account_ids = [(6 ,0 , nix_payment_account_ids)])
        return res


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = 'account.payment.line.create'

    def _prepare_move_line_domain(self):
        conf = self.env['ir.config_parameter']
        res = super(AccountPaymentLineCreate, self)._prepare_move_line_domain()
        payment_account_ids = conf.get_param('l10n_se_account_payment_order.payment_account_ids')
        nix_payment_account_ids = conf.get_param('l10n_se_account_payment_order.nix_payment_account_ids')
        if nix_payment_account_ids:
            # add accounts should not include in payment
            nix_payment_account_ids = nix_payment_account_ids.split(",")
            res += [('account_id.id', 'not in', nix_payment_account_ids)]
        if payment_account_ids:
            for e in res:
                # add specified accounts which are not defined as internal_type: payable
                if e[0] == 'account_id.internal_type':
                    internal_type_domain = e
                    res.remove(e)
                    payment_account_ids = payment_account_ids.split(",")
                    res += ['|', internal_type_domain, ('account_id.id', 'in', payment_account_ids)]
                    break
        _logger.warning(f"jakmar: domain {res}")
        return res
        
        
        
        

# ~ 2021-08-25 07:14:31,363 258992 WARNING config_is_awful odoo.addons.l10n_se_account_payment_order.res_config: jakmar: domain [('reconciled', '=', False), ('company_id', '=', 1), ('blocked', '!=', True), '|', ('date_maturity', '<=', datetime.date(2022, 6, 30)), ('date_maturity', '=', False), ('credit', '>', 0), '|', ('account_id.internal_type', 'in', ['payable', 'receivable']), ('account_id.id', 'in', ['55', '887'])] 

