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
import re

    
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
            _logger.info(u"Try parsing with SEB Kontohändelser.")
            parser = Parser(base64.b64decode(self.data_file))
        except ValueError:
            # Not a SEB file, returning super will call next candidate:
            _logger.info(u"Statement file was not a SEB Kontohändelse file.")
            return super(AccountBankStatementImport, self)._parse_all_files(data_file)

        fakt = re.compile('\d+')  # Pattern to find invoice numbers
        seb = parser.parse()
        for s in seb.statements:
            for t in s['transactions']:
                #raise Warning(t)
                partner_id = self.env['res.partner'].search([('name','ilike',t['partner_name'])])
                if partner_id:
                    t['account_number'] = partner_id[0].bank_ids and partner_id[0].bank_ids[0].acc_number or ''
                    t['partner_id'] = partner_id[0].id
                fnr = '-'.join(fakt.findall(t['name']))
                if fnr:
                    invoice = self.env['account.invoice'].search(['|',('name','ilike',fnr),('supplier_invoice_number','ilike',fnr)])
                    if invoice:
                        t['account_number'] = invoice[0] and  invoice[0].partner_id.bank_ids and invoice[0].partner_id.bank_ids[0].acc_number or ''
                        t['partner_id'] = invoice[0] and invoice[0].partner_id.id or None
        #~ res = parser.parse(data_file)
        #_logger.debug("res: %s" % seb.statements)
        #raise Warning(seb.statements)
        return seb.statements

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
