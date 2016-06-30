# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
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
from openerp import api,models, _
from .swedbank import SwedbankTransaktionsrapport as Parser
import cStringIO

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        """Parse a Swedbank transaktionsrapport  file."""
        try:
            _logger.debug("Try parsing with swedbank_transaktioner.")
            parser = Parser(data_file)
            swedbank = parser.parse()
        except ValueError:
            # Not a Swedbank file, returning super will call next candidate:
            _logger.error("Statement file was not a Swedbank Transaktionsrapport file.",exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)


#        bankstatement = BankStatement()
#        bankstatement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
#        bankstatement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
        transactions = []
        total_amt = 0.00
        try:
            for transaction in swedbank:
                bank_account_id = partner_id = False
                
                if transaction['referens']:
                    banks = self.pool['res.partner.bank'].search(cr,uid,
                        [('owner_name', '=', transaction['referens'])], limit=1)
                    if banks:
                        bank_account = self.browse(cr,uid,banks[0])
                        bank_account_id = bank_account.id
                        partner_id = bank_account.partner_id.id
                vals_line = {
                    'date': transaction['bokfdag'],  # bokfdag, transdag, valutadag
                    'name': transaction['referens'] + (
                        transaction['text'] and ': ' + transaction['text'] or ''),
                    'ref': transaction['radnr'],
                    'amount': transaction['belopp'],
                    'unique_import_id': transaction['radnr'],
                    'bank_account_id': bank_account_id or None,
                    'partner_id': partner_id or None,
                }
                if not vals_line['name']:
                    vals_line['name'] = transaction['produkt'].capitalize()
                total_amt += float(transaction['belopp'])
                transactions.append(vals_line)
        except Exception, e:
            raise Warning(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message
            ))

        vals_bank_statement = {
            'name': swedbank.account.name,
            'transactions': transactions,
            'balance_start': swedbank.account.balance_start,
            'balance_end_real':
                float(swedbank.account.balance_start) + total_amt,
        }
        return swedbank.account.currency, swedbank.account.number, [
            vals_bank_statement]


class AccountBankSwishImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.multi
    def _parse_file(self,data_file):
        """Parse a Swedbank swish  file."""
        try:
            parser = Parser(data_file)
            _logger.debug("Try parsing with swedbank_swish.")
            swedbank = parser.parse()
        except ValueError:
            # Not a Swedbank file, returning super will call next candidate:
            _logger.debug("Statement file was not a Swedbank Swish file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(data_file)


#        bankstatement = BankStatement()
#        bankstatement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
#        bankstatement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
        transactions = []
        total_amt = 0.00
        try:
            for transaction in swedbank:
                bank_account_id = partner_id = False
                
                if transaction['referens']:
                    banks = self.pool['res.partner.bank'].search(cr,uid,
                        [('owner_name', '=', transaction['referens'])], limit=1)
                    if banks:
                        bank_account = self.browse(cr,uid,banks[0])
                        bank_account_id = bank_account.id
                        partner_id = bank_account.partner_id.id
                vals_line = {
                    'date': transaction['bokfdag'],  # bokfdag, transdag, valutadag
                    'name': transaction['referens'] + (
                        transaction['text'] and ': ' + transaction['text'] or ''),
                    'ref': transaction['radnr'],
                    'amount': transaction['belopp'],
                    'unique_import_id': transaction['radnr'],
                    'bank_account_id': bank_account_id or None,
                    'partner_id': partner_id or None,
                }
                if not vals_line['name']:
                    vals_line['name'] = transaction['produkt'].capitalize()
                total_amt += float(transaction['belopp'])
                transactions.append(vals_line)
        except Exception, e:
            raise Warning(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message
            ))

        vals_bank_statement = {
            'name': swedbank.account.routing_number,
            'transactions': transactions,
            'balance_start': swedbank.account.balance_start,
            'balance_end_real':
                float(swedbank.account.balance_start) + total_amt,
        }
        return swedbank.account.currency, swedbank.account.number, [
            vals_bank_statement]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
