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
import base64
import logging
from odoo import api,models, _
from .handelsbanken import HandelsbankenTransaktionsrapport as Parser
import uuid

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.statement.import'

    @api.model
    def _parse_file(self, statement_file):
        """Parse a Handelsbanken transaktionsrapport  file."""
        try:
            _logger.debug("Try parsing with handelsbanken_transaktioner.")
            parser = Parser(base64.b64decode(self.statement_file))
            handelsbanken = parser.parse()
        except ValueError:
            # Not a Handelsbanken file, returning super will call next candidate:
            _logger.error("Statement file was not a Handelsbanken Transaktionsrapport file.",exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(statement_file)


        transactions = []
        total_amt = 0.00
        try:
            for index, transaction in enumerate(handelsbanken.statements):
                bank_account_id = partner_id = False
                ref = ''
                if transaction['Referens']:
                    ref = transaction['Referens'].strip()
                    partner_id = self.env['res.partner'].search(['|','|','|',('name','ilike',ref),('ref','ilike',ref),('name','ilike',ref.split(' ')[0]),('ref','ilike',ref.split(' ')[0])])
                    if partner_id:
                        bank_account_id = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].id or None
                        partner_id = partner_id[0].commercial_partner_id.id

                #Prep alternative date
                start_date = transaction['Datum intervall'].split(' ')
                _logger.warning(f"Start date is: {start_date}")

                vals_line = {
                    'date': transaction[u'Bokföringsdag'] or start_date[0],  # bokfdag, transdag, valutadag
                    'payment_ref': ref + (transaction['Kontohavare'] and ': ' + transaction['Kontonr'] or ''),
                    'ref': transaction['Referens'],
                    'amount': transaction[u'Insättning/Uttag'].replace(",","."),
                    'unique_import_id': ''.join((str(index), str(transaction[u'Bokföringsdag']), str(transaction[u'Insättning/Uttag']))),
                    'partner_bank_id': bank_account_id or None,
                    'partner_id': partner_id or None,
                }
                if not vals_line['payment_ref']:
                    vals_line['payment_ref'] = transaction['Kontohavare'].capitalize()
                total_amt += 0.0 if transaction[u'Insättning/Uttag'] == '' else float(transaction[u'Insättning/Uttag'].replace(",","."))
                transactions.append(vals_line)
        except KeyError as e:
            raise Warning(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e
            ))
        vals_bank_statement = {
            'transactions': transactions,
            'name': handelsbanken.account.pref,
            'date': handelsbanken.account.date,
            'currency_code': handelsbanken.account.currency,
            'account_number': handelsbanken.account.number,
            'balance_start': handelsbanken.account.balance_start,
            'balance_end': handelsbanken.account.balance_end,
            'balance_end_real':
                float(handelsbanken.account.balance_start) + total_amt,
        }
        return handelsbanken.account.currency, handelsbanken.account.number, [
            vals_bank_statement]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
