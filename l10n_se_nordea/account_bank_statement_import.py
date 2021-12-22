# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015-2020 Vertel AB <http://vertel.se>
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
from datetime import datetime
import logging
import re
from odoo import api,models, _
from odoo.exceptions import UserError
from .nordea import NordeaTransaktionsrapport as Parser
import uuid
import base64

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add nordea method to account.bank.statement.import."""
    _inherit = 'account.statement.import'

    @api.model
    def _parse_file(self, statement_file):
        """Parse a Nordbanken transaktionsrapport  file."""
        try:
            _logger.debug("Try parsing with nordea_transaktioner.")
            parser = Parser(base64.b64decode(self.statement_file))
            nordea = parser.parse()
        except ValueError:
            # Not a Nordbanken file, returning super will call next candidate:
            _logger.error("Statement file was not a Nordea Transaktionsrapport file.",exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(statement_file)

        account_name = self.statement_filename.split(' - ', 1)
        account_number = re.search("\d{2}\s\d{2}\s\d{2}\D\d{1}", self.statement_filename)

        transactions = []
        total_amt = 0.00
        try:
            for i, transaction in enumerate(nordea):
                # _logger.error('%s' % transaction)
                partner_bank_id = partner_id = False
                ref = ''
                if transaction['Meddelande']:
                    ref = transaction['Meddelande'].strip()
                    partner_id = self.env['res.partner'].search(['|','|','|',('name','ilike',ref),('ref','ilike',ref),('name','ilike',ref.split(' ')[0]),('ref','ilike',ref.split(' ')[0])])
                    if partner_id:
                        partner_bank_id = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].id or None
                        partner_id = partner_id[0].commercial_partner_id.id
                if 'period_id' not in transaction:
                    if isinstance(transaction['\ufeffBokföringsdag'], str):
                        transaction['\ufeffBokföringsdag'] = datetime.strptime(transaction['\ufeffBokföringsdag'], '%Y-%m-%d').date()
                    transaction['period_id'] = self.env['account.period'].date2period(transaction['\ufeffBokföringsdag']).id
                    if transaction['period_id'] == False:
                        raise UserError(_('A fisical year has not been configured. Please configure a fisical year.'))
                vals_line = {
                    'date': transaction['\ufeffBokföringsdag'],  # bokfdag, transdag, valutadag
                    'payment_ref': ref + ' ' + (transaction['Rubrik']),
                    'ref': transaction['Meddelande'],
                    'amount': transaction['Belopp'].replace(",","."),
                    'narration': 'Avsändare: ' + str(transaction['Avsändare']) + '\nMottagare: ' + str(transaction['Mottagare']) + '\nTyp: ' + str(transaction['Typ']),
                    'unique_import_id': 'nordea %s - %s' % (account_number.group(), i),
                    'partner_bank_id': partner_bank_id or None,
                    'partner_id': partner_id or None,
                    'period_id': transaction['period_id']
                }
                if not vals_line['payment_ref']:
                    vals_line['payment_ref'] = transaction['Rubrik'].capitalize()
                total_amt += float(transaction['Belopp'].replace(",","."))
                transactions.append(vals_line)
        except Exception as e:
            raise e
            # raise Warning(_(
            #     "The following problem occurred during import. "
            #     "The file might not be valid.\n\n %s" % e
            # ))

        vals_bank_statement = {
            'transactions': transactions,
            'name': account_name[0],
            'currency_code': nordea.currency,
            'account_number': account_number.group(),
            'balance_start': nordea.balance_start,
            'balance_end_real':
                float(nordea.balance_start) + total_amt,
        }
        return nordea.currency, account_number.group(), [
            vals_bank_statement]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
