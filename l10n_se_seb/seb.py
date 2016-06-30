# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import base64
from openerp.addons.account_bank_statement_import.parserlib import (
    BankStatement)


import logging
_logger = logging.getLogger(__name__)

from xlrd import open_workbook, XLRDError
from xlrd.book import Book
from xlrd.sheet import Sheet

import sys

class SEBTransaktionsrapport(object):
    """Parser for Swedbank Transaktionsrapport import files."""
    
    def __init__(self, data_file):
        self.row = 0
        try:
            #~ self.data_file = open_workbook(file_contents=data_file)
            self.data = open_workbook(file_contents=data_file).sheet_by_index(0)
        except XLRDError, e:
            _logger.error(u'Could not read file (SEB Kontohändelser.xlsx)')
            raise ValueError(e)  
        self.rows = self.data.nrows - 9
        _logger.error(u'Rows %s' % self.rows)

        self.header = [c.value.lower() for c in self.data.row(8)]
        _logger.error(u'Header %s' % self.header)

        self.balance_start = 0.0
        self.balance_end_real = 0.0
        self.balance_end = 0.0
        self.statements = []
        

    def parse(self):
        """Parse swedbank transaktionsrapport bank statement file contents."""
        if not (self.data.cell(0,0).value[:13] == u'Företagsnamn:' and self.data.cell(3,0).value[:11] == u'Sökbegrepp:'):
            _logger.error(u'Row 0 %s (was looking for Företagsnamn) %s %s' % (self.data.cell(0,0).value[:13],self.data.cell(3,0).value[:11],self.data.row(3)))
            raise ValueError('This is not a SEB Transaktionsrapport')
            
        self.balance_start = float(self.data.cell(self.rows,5).value - self.data.cell(self.rows,4).value)
        self.balance_end_real = float(self.data.cell(6,1).value)
        self.balance_end = float(self.data.cell(6,1).value)


        self.account_currency = 'SEK' # self.env['res.currency'].search('co')1 # 'SEK'
        self.account_number = self.data.cell(6,0).value
        self.name = self.data.cell(0,0).value[15:30]


        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today() # t[u'bokföringsdatum'] # bokföringsdatum,valutadatum
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number        
        for t in SEBIterator(self.data,header_row=8):
            _logger.error('Transaction %s' % t)          

            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = float(t['belopp'])
            transaction.eref = t['verifikationsnummer'].strip()
            transaction.name = t['text/mottagare'].strip()
            transaction.note = t['text/mottagare'].strip()
            transaction.remote_owner = t['text/mottagare'].strip()
            transaction.value_date = t[u'bokföringsdatum'] # bokföringsdatum,valutadatum
            transaction.unique_import_id = t['verifikationsnummer'].strip()
            #~ transaction.message
            #self.current_statement.end_balance = 
        
        self.statements.append(self.current_statement)

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

        _logger.error('Statement %s Transaktioner %s' % (self.statements,''))
        return self

class SEBIterator(object):
    def __init__(self, data,header_row=8):
        self.row = header_row + 1 # First data-row
        self.data = data
        self.header = [c.value.lower() for c in data.row(header_row)]
            
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.data.nrows:
            raise StopIteration
        r = self.data.row(self.row)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
