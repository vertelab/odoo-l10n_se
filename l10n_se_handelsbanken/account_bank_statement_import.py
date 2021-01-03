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
import hashlib

import logging
from odoo import api,models, _
from .handelsbanken import HandelsbankenTransaktionsrapport as Parser
import cStringIO
import uuid

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a Handelsbanken transaktionsrapport  file."""
        try:
            _logger.debug("Try parsing with handelsbanken_transaktioner.")
            parser = Parser(data_file)
            handelsbanken = parser.parse()
        except ValueError:
            # Not a Handelsbanken file, returning super will call next candidate:
            _logger.error("Statement file was not a Handelsbanken Transaktionsrapport file.",exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(data_file)


#        bankstatement = BankStatement()
#        bankstatement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
#        bankstatement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
        transactions = []
        total_amt = 0.00
        try:
            for index, transaction in enumerate(handelsbanken):
                bank_account_id = partner_id = False
                ref = ''
                if transaction['Referens']:
                    ref = transaction['Referens'].strip()
                    partner_id = self.env['res.partner'].search(['|','|','|',('name','ilike',ref),('ref','ilike',ref),('name','ilike',ref.split(' ')[0]),('ref','ilike',ref.split(' ')[0])])
                    if partner_id:
                        bank_account_id = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].id or None
                        partner_id = partner_id[0].commercial_partner_id.id
                # ~ Kontohavare;Kontonr;IBAN;BIC;Kontoform;Valuta;Kontoförande kontor;Datum intervall;Kontor;Bokföringsdag;
                # ~ Reskontradag;Valutadag;Referens;Insättning/Uttag;Bokfört saldo;Aktuellt saldo;Valutadagssaldo;Referens Swish;Avsändar-id Swish;
                _logger.error('Transaction :: %s' % transaction['Referens'])
                _logger.error('Transaction :: %s' % transaction['Bokforingsdag'])
                _logger.error('Transaction :: %s' % transaction)

                vals_line = {
                    # ~ 'date': transaction['bokfdag'],  # bokfdag, transdag, valutadag
                    # ~ 'name': ref + (transaction['text'] and ': ' + transaction['text'] or ''),
                    # ~ 'ref': transaction['referens'],
                    # ~ 'amount': transaction['belopp'],
                    # ~ 'unique_import_id': 'handelsbanken %s %s' % (handelsbanken.account.name[29:52], transaction['radnr']),
                    # ~ 'bank_account_id': bank_account_id or None,
                    # ~ 'partner_id': partner_id or None,
                    'date': transaction[u'Bokforingsdag'],  # bokfdag, transdag, valutadag
                    'name': ref + (transaction['Kontohavare'] and ': ' + transaction['Kontonr'] or ''),
                    'ref': transaction['Referens'],
                    #'amount': transaction[u'Bokfört saldo'],
                    'amount': transaction[u'Insättning/Uttag'],
                    #'unique_import_id': 'handelsbanken %s %s' % (transaction['Kontoform'], transaction['Kontonr']),
                    # Making an unique string to satisfy Odoo as we have no real unique data to identify a transaction
                    'unique_import_id': hashlib.md5(''.join((str(index), str(transaction[u'Bokforingsdag']), str(transaction[u'Insättning/Uttag'])))).hexdigest(),
                    'bank_account_id': bank_account_id or None,
                    'partner_id': partner_id or None,
                }
                if not vals_line['name']:
                    vals_line['name'] = transaction['Kontohavare'].capitalize()
                total_amt += float(transaction[u'Insättning/Uttag'])
                transactions.append(vals_line)
        except KeyError, e:
        #except Exception, e:
            raise Warning(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message
            ))
        vals_bank_statement = {
            'name': handelsbanken.account.name,
            'transactions': transactions,
            'balance_start': handelsbanken.account.balance_start,
            'balance_end_real':
                float(handelsbanken.account.balance_start) + total_amt,
        }
        return handelsbanken.account.currency, handelsbanken.account.number, [
            vals_bank_statement]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
