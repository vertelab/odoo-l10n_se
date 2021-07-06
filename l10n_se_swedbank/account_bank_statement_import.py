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
from odoo import api,models, _
from .swedbank import SwedbankTransaktionsrapport as Parser
import cStringIO
import uuid

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a Swedbank transaktionsrapport  file."""
        try:
            _logger.debug("Try parsing with swedbank_transaktioner.")
            parser = Parser(data_file)
            swedbank = parser.parse()
        except ValueError as e:
            # Not a Swedbank file, returning super will call next candidate:
            _logger.error("Statement file was not a Swedbank Transaktionsrapport file.",exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(data_file)


#        bankstatement = BankStatement()
#        bankstatement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
#        bankstatement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
        transactions = []
        total_amt = 0.00
        try:
            for transaction in swedbank:
                bank_account_id = partner_id = False
                ref = ''
                if transaction['referens']:
                    ref = transaction['referens'].strip()
                    partner_id = self.env['res.partner'].search(['|','|','|',('name','ilike',ref),('ref','ilike',ref),('name','ilike',ref.split(' ')[0]),('ref','ilike',ref.split(' ')[0])])
                    if partner_id:
                        bank_account_id = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].id or None
                        partner_id = partner_id[0].commercial_partner_id.id
                vals_line = {
                    'date': transaction['bokfdag'],  # bokfdag, transdag, valutadag
                    'name': ref + (transaction['text'] and ': ' + transaction['text'] or ''),
                    'ref': transaction['referens'],
                    'amount': transaction['belopp'],
                    'unique_import_id': 'swedbank %s %s' % (swedbank.account.name[29:52], transaction['radnr']),
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
