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
from openerp import models
from .swedbank import SwedbankTransaktionsrapport as Parser

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        """Parse a Swedbank transaktionsrapport  file."""
        parser = Parser()
        try:
            _logger.debug("Try parsing with swedbank_transaktioner.")
            swedbank = Parser.parse(data_file)
        except ValueError:
            # Not a Swedbank file, returning super will call next candidate:
            _logger.debug("Statement file was not a Swedbank Transaktionsrapport file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)


        transactions = []
        total_amt = 0.00
        try:
            for transaction in swedbank.transactions:
                bank_account_id = partner_id = False
                if transaction.payee:
                    banks = self.env['res.partner.bank'].search(
                        [('owner_name', '=', transaction.payee)], limit=1)
                    if banks:
                        bank_account = banks[0]
                        bank_account_id = bank_account.id
                        partner_id = bank_account.partner_id.id
                vals_line = {
                    'date': transaction.date,
                    'name': transaction.payee + (
                        transaction.memo and ': ' + transaction.memo or ''),
                    'ref': transaction.id,
                    'amount': transaction.amount,
                    'unique_import_id': transaction.id,
                    'bank_account_id': bank_account_id,
                    'partner_id': partner_id,
                }
                # Memo (<NAME>) and payee (<PAYEE>) are not required
                # field in OFX statement, cf section 11.4.3 Statement
                # Transaction <STMTTRN> of the OFX specs: the required
                # elements are in bold, cf 1.5 Conventions and these 2
                # fields are not in bold.
                # But the 'name' field of account.bank.statement.line is
                # required=True, so we must always have a value !
                # The field TRNTYPE is a required field in OFX
                if not vals_line['name']:
                    vals_line['name'] = transaction.type.capitalize()
                    if transaction.checknum:
                        vals_line['name'] += ' %s' % transaction.checknum
                total_amt += float(transaction.amount)
                transactions.append(vals_line)
        except Exception, e:
            raise UserError(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message
            ))

        vals_bank_statement = {
            'name': swedbank.account.routing_number,
            'transactions': transactions,
            'balance_start': swedbank.account.statement.balance,
            'balance_end_real':
                float(swedbank.account.statement.balance) + total_amt,
        }
        return swedbank.account.statement.currency, swedbank.account.number, [
            vals_bank_statement]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
