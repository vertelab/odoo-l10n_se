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
from .seb import SEBTransaktionsrapport as Parser
import base64

    
from StringIO import StringIO
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    #~ def import_file(self):
        #~ """Process the file chosen in the wizard, create bank statement(s) and
        #~ go to reconciliation."""
        #~ self.ensure_one()
        #~ data_file = base64.b64decode(self.data_file)
        #~ # pylint: disable=protected-access
        #~ statement_ids, notifications = self.with_context(
            #~ active_id=self.id  # pylint: disable=no-member
        #~ )._import_file(data_file)
        #~ # dispatch to reconciliation interface
        #~ action = self.env.ref(
            #~ 'account.action_bank_reconcile_bank_statements')
        #~ return {
            #~ 'name': action.name,
            #~ 'tag': action.tag,
            #~ 'context': {
                #~ 'statement_ids': statement_ids,
                #~ 'notifications': notifications
            #~ },
            #~ 'type': 'ir.actions.client',
        #~ }


    @api.model
    def _parse_all_files(self, data_file):
        """Parse one file or multiple files from zip-file.

        Return array of statements for further processing.
        
        xlsx-files are a Zip-file, have to override
        """
        statements = []
        files = [data_file]
        
        try:
            _logger.info("Try parsing with seb_transaktioner.")
            parser = Parser(base64.b64decode(self.data_file))
        except ValueError:
            # Not a SEB file, returning super will call next candidate:
            _logger.info(u"Statement file was not a SEB Kontohändelse file.")
            return super(AccountBankStatementImport, self)._parse_all_files(data_file)

        seb = parser.parse()
        _logger.info(u"Statement file %s." % seb)
        
        #~ res = parser.parse(data_file)
        _logger.debug("res: %s" % seb)
        return seb.statements



    #~ @api.multi
    #~ def _parse_file(self,data_file):
        #~ """Parse a SEB Kontohändelser file."""
        #~ try:
            #~ _logger.info("Try parsing with seb_transaktioner.")
            #~ parser = Parser(base64.b64decode(self.data_file))
        #~ except ValueError:
            #~ # Not a SEB file, returning super will call next candidate:
            #~ _logger.info(u"Statement file was not a SEB Kontohändelse file.")
            #~ return super(AccountBankStatementImport, self)._parse_file(data_file)

        #~ seb = parser.parse()
        #~ _logger.info(u"Statement file %s." % seb)
        
        res = parser.parse(data_file)
        #~ _logger.debug("res: %s" % seb)
        #~ return seb.account_currency, seb.account_number, [seb.statements]
#        bankstatement = BankStatement()
#        bankstatement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
#        bankstatement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
        #~ transactions = []
        #~ total_amt = 0.00
        #~ try:
            #~ for transaction in seb:
                #~ _logger.info(u"Statement file %s." % transaction)
                #~ bank_account_id = partner_id = False
                
                #~ if transaction['referens']:
                    #~ banks = self.pool['res.partner.bank'].search(cr,uid,
                        #~ [('owner_name', '=', transaction['referens'])], limit=1)
                    #~ if banks:
                        #~ bank_account = self.browse(cr,uid,banks[0])
                        #~ bank_account_id = bank_account.id
                        #~ partner_id = bank_account.partner_id.id
                #~ vals_line = {
                    #~ 'date': transaction['bokfdag'],  # bokfdag, transdag, valutadag
                    #~ 'name': transaction['referens'] + (
                        #~ transaction['text'] and ': ' + transaction['text'] or ''),
                    #~ 'ref': transaction['radnr'],
                    #~ 'amount': transaction['belopp'],
                    #~ 'unique_import_id': transaction['radnr'],
                    #~ 'bank_account_id': bank_account_id or None,
                    #~ 'partner_id': partner_id or None,
                #~ }
                #~ if not vals_line['name']:
                    #~ vals_line['name'] = transaction['produkt'].capitalize()
                #~ total_amt += float(transaction['belopp'])
                #~ transactions.append(vals_line)
        #~ except Exception, e:
            #~ raise Warning(_(
                #~ "The following problem occurred during import. "
                #~ "The file might not be valid.\n\n %s" % e.message
            #~ ))

        vals_bank_statement = {
            'name': seb.account.name,
            'transactions': transactions,
            'balance_start': seb.account.balance_start,
            'balance_end_real':
                float(seb.account.balance_start) + total_amt,
        }
        return seb.account.currency, seb.account.number, [
            vals_bank_statement]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
