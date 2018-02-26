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
from .seb import SEBTransaktionsrapportType1 as Parser
from .seb import SEBTransaktionsrapportType2 as Parser2
from .seb import SEBTransaktionsrapportType3 as Parser3
import base64
import re

from openerp.osv import osv
    
from StringIO import StringIO
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add seb method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_all_files(self, data_file):
        """Parse one file or multiple files from zip-file.
        Return array of statements for further processing.
        xlsx-files are a Zip-file, have to override
        """
        statements = []
        files = [data_file]
        
        try:
            _logger.info(u"Try parsing with SEB Typ 1 Kontohändelser.")
            parser = Parser(base64.b64decode(self.data_file))
        except ValueError:
            # Not a SEB Type 1 file, returning super will call next candidate:
            _logger.info(u"Statement file was not a SEB Type 1 Kontohändelse file.")
            try:
                _logger.info(u"Try parsing with SEB Typ 2 Kontohändelser.")
                parser = Parser2(base64.b64decode(self.data_file)) 
            except ValueError:
                # Not a SEB Type 2 file, returning super will call next candidate:
                _logger.info(u"Statement file was not a SEB Type 2 Kontohändelse file.")
                try:
                    _logger.info(u"Try parsing with SEB Typ 3 Kontohändelser.")
                    parser = Parser3(base64.b64decode(self.data_file)) 
                except ValueError:
                    # Not a SEB Type 3 file, returning super will call next candidate:
                    _logger.info(u"Statement file was not a SEB Type 3 Kontohändelse file.")
                    return super(AccountBankStatementImport, self)._parse_all_files(data_file)

        fakt = re.compile('\d+')  # Pattern to find invoice numbers
        seb = parser.parse()
        for s in seb.statements:
            currency = self.env['res.currency'].search([('name','=',s['currency_code'])])
            for t in s['transactions']:
                #raise Warning(t)
                t['currency_id'] = currency.id
                partner_id = self.env['res.partner'].search(['|',('name','ilike',t['partner_name']),('ref','ilike',t['partner_name'])]) # ,('ref','ilike',t['partner_name']),('phone','ilike',t['partner_name'])])
                if partner_id:
                    t['account_number'] = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner_id[0].commercial_partner_id.id
                fnr = '-'.join(fakt.findall(t['name']))
                if fnr:
                    invoice = self.env['account.invoice'].search(['|',('name','ilike',fnr),('supplier_invoice_number','ilike',fnr)])
                    if invoice:
                        t['account_number'] = invoice[0] and  invoice[0].partner_id.bank_ids and invoice[0].partner_id.bank_ids[0].acc_number or ''
                        t['partner_id'] = invoice[0] and invoice[0].partner_id.id or None
                # account.voucher / account.move  t['journal_entry_id']
                
        #~ res = parser.parse(data_file)
        _logger.debug("res: %s" % seb.statements)
        #~ raise Warning(seb.statements)
        return seb.statements

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement.line'
    
    def get_move_lines_for_reconciliation_by_statement_line_id(self, cr, uid, st_line_id, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Bridge between the web client reconciliation widget and get_move_lines_for_reconciliation (which expects a browse record) """
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        st_line = self.browse(cr, uid, st_line_id, context=context)
        return self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids, str, offset, limit, count, additional_domain, context=context)
    
    def get_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Find the move lines that could be used to reconcile a statement line. If count is true, only returns the count.

            :param st_line: the browse record of the statement line
            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param boolean count: just return the number of records
            :param tuples list additional_domain: additional domain restrictions
        """
        _logger.warn('st_line: %s' % st_line)
        _logger.warn('st_line.name: %s' % st_line.name)
        _logger.warn('st_line.currency_id: %s' % st_line.currency_id)
        _logger.warn('excluded_ids: %s' % excluded_ids)
        _logger.warn('str: %s' % str)
        _logger.warn('limit: %s' % limit)
        _logger.warn('additional_domain: %s' % additional_domain)
        mv_line_pool = self.pool.get('account.move.line')
        domain = self._domain_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, str=str, additional_domain=additional_domain, context=context)
        _logger.warn('domain: %s' % domain)
        # Get move lines ; in case of a partial reconciliation, only keep one line (the first whose amount is greater than
        # the residual amount because it is presumably the invoice, which is the relevant item in this situation)
        filtered_lines = []
        reconcile_partial_ids = []
        actual_offset = offset
        while True:
            line_ids = mv_line_pool.search(cr, uid, domain, offset=actual_offset, limit=limit, order="date_maturity asc, id asc", context=context)
            lines = mv_line_pool.browse(cr, uid, line_ids, context=context)
            make_one_more_loop = False
            for line in lines:
                if line.reconcile_partial_id and \
                        (line.reconcile_partial_id.id in reconcile_partial_ids or \
                        abs(line.debit - line.credit) < abs(line.amount_residual)):
                    #if we filtered a line because it is partially reconciled with an already selected line, we must do one more loop
                    #in order to get the right number of items in the pager
                    make_one_more_loop = True
                    continue
                filtered_lines.append(line)
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)

            if not limit or not make_one_more_loop or len(filtered_lines) >= limit:
                break
            actual_offset = actual_offset + limit
        lines = limit and filtered_lines[:limit] or filtered_lines

        # Either return number of lines
        if count:
            return len(lines)

        # Or return list of dicts representing the formatted move lines
        else:
            target_currency = st_line.currency_id or st_line.journal_id.currency or st_line.journal_id.company_id.currency_id

            mv_lines = mv_line_pool.prepare_move_lines_for_reconciliation_widget(cr, uid, lines, target_currency=target_currency, target_date=st_line.date, context=context)
            #~ raise Warning(target_currency.name,mv_lines)
            has_no_partner = not bool(st_line.partner_id.id)
            for line in mv_lines:
                line['has_no_partner'] = has_no_partner
            #~ from pprint import PrettyPrinter
            #~ _logger.warn('\nmv_lines:\n%s' % PrettyPrinter(indent=4).pformat(mv_lines))
            return mv_lines


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
