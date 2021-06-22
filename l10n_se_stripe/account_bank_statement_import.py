# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import logging
from openerp import api,models,fields, _
from .stripe import StripePaymentsReport as Parser
import cStringIO
import uuid
import base64

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add Stripe method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse one file or multiple files from zip-file.
        Return array of statements for further processing.
        xlsx-files are a Zip-file, have to override
        """
        statements = []
        files = [data_file]

        try:
            _logger.info(u"Try parsing with Stripe Report file.")
            parser = Parser(data_file)
        except ValueError:
            _logger.info(u"Statement file was not a Stripe Report file.")
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        #fakt = re.compile('\d+')  # Pattern to find invoice numbers

        stripe = parser.parse()
        for s in stripe.statements:
            currency = self.env['res.currency'].search([('name','=',s['currency_code'])])
            account = self.env['res.partner.bank'].search([('acc_number','=',s['account_number'])]).mapped('journal_id').mapped('default_debit_account_id')
            move_line_ids = []
            for t in s['transactions']:
                t['currency_id'] = currency.id
                partner_id = self.env['res.partner'].search([('email', '=', t['name'].split(',')[0])])
                if partner_id:
                    t['account_number'] = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner_id[0].commercial_partner_id.id
                #d1 = fields.Date.to_string(fields.Date.from_string(t['date']) - timedelta(days=5))
                #d2 = fields.Date.to_string(fields.Date.from_string(t['date']) + timedelta(days=40))
                line = self.env['account.move.line'].search(
                    [('partner_id', '=', partner_id.id),
                     ('balance', '=', t['amount']),
                     ('name', 'ilike', str(t['ref']))])
                if len(line) > 0:
                    if line[0].move_id.state == 'draft':# and line[0].move_id.date != t['date']:
                        line[0].move_id.date = t['value_date']
                    t['journal_entry_id'] = line[0].move_id.id
                    for line in line[0].move_id.line_ids:
                        move_line_ids.append(line)
            s['move_line_ids'] = [(6, 0, [l.id for l in move_line_ids])]

        _logger.debug("res: %s" % stripe.statements)
        return stripe.account_currency, stripe.account_number, stripe.statements

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
