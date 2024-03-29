# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018- Vertel AB (<http://vertel.se>).
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
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
import base64
from odoo.addons.l10n_se_account_bank_statement_import.account_bank_statement_import import BankStatement


import logging
_logger = logging.getLogger(__name__)

from xlrd import open_workbook, XLRDError
from xlrd.book import Book
from xlrd.sheet import Sheet

import sys

class SKVTransaktionsrapportType1(object):
    """Parser for SKV Kontohändelser import files."""

    def __init__(self, data_file):
        try:
            #~ self.data_file = open_workbook(file_contents=data_file)
            self.data = open_workbook(file_contents=data_file).sheet_by_index(0)
        except XLRDError as e:
            _logger.error(u'Could not read file (SEB Kontohändelser.xlsx)')
            raise ValueError(e)
        if not (self.data.cell(0,0).value[:13] == u'Företagsnamn:' and self.data.cell(3,0).value[:11] == u'Sökbegrepp:'):
            _logger.error(u'Row 0 %s (was looking for Företagsnamn) %s %s' % (self.data.cell(0,0).value[:13],self.data.cell(3,0).value[:11],self.data.row(3)))
            raise ValueError(u'This is not a SEB Kontohändelser')

        self.nrows = self.data.nrows - 1
        self.header = []
        self.statements = []

    def parse(self):
        """Parse SKV transaktionsrapport bank statement file contents type 1."""

        self.account_currency = 'SEK'
        self.header = [c.value.lower() for c in self.data.row(8)]
        self.account_number = self.data.cell(6,0).value
        self.name = self.data.cell(0,0).value[15:30]

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today() # t[u'bokföringsdatum'] # bokföringsdatum,valutadatum
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number
        self.current_statement.statement_id = '%s %s' % (self.data.cell(0,0).value[14:],self.data.cell(2,0).value[6:])
        self.current_statement.start_balance = float(self.data.cell(self.nrows,5).value - self.data.cell(self.nrows,4).value)
        self.current_statement.end_balance = float(self.data.cell(9,5).value)
        for t in SKVIterator(self.data,header_row=8):
            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = float(t['belopp'])
            transaction.eref = t['verifikationsnummer'].strip()
            transaction.name = t['text/mottagare'].strip()
            transaction.note = t['text/mottagare'].strip()
            transaction.value_date = t[u'bokföringsdatum'] # bokföringsdatum,valutadatum
            transaction.unique_import_id = t['verifikationsnummer'].strip()
            transaction.remote_owner = t['text/mottagare'].strip()
            #~ transaction.message
            #self.current_statement.end_balance =

        self.statements.append(self.current_statement)
#        _logger.error('Statement %s Transaktioner %s' % (self.statements,''))
        return self


class SKVIterator(object):
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

    def __next__(self):
        if self.row >= self.data.nrows:
            raise StopIteration
        r = self.data.row(self.row)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
