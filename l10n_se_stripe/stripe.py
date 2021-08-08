# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2021 Vertel AB <http://vertel.se>
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
from openerp import models, fields, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import base64
from openerp.addons.account_bank_statement_import.parserlib import BankStatement
import hashlib

import logging
_logger = logging.getLogger(__name__)
try:
    from xlrd import open_workbook, XLRDError
    from xlrd.book import Book
    from xlrd.sheet import Sheet
except:
    _logger.info('xlrd not installed.')

class StripePaymentsReport(object):
    """Parser for Stripe Kontohändelser import files."""

    def __init__(self, data_file):
        try:
            self.data = open_workbook(file_contents=data_file).sheet_by_index(0)
        except XLRDError, e:
            _logger.error(u'Could not read file')
            raise ValueError(e)
        if not self.data.cell(0,0).value == 'id' and not self.data.cell(0,1).value == 'Description':
            _logger.error(u'Row 0 %s (was looking for id and Description)')
            raise ValueError(u'This is not a Stripe Report')

        self.nrows = self.data.nrows - 3
        self.header = []
        self.statements = []

    def parse(self):
        """Parse stripe transaktionsrapport bank statement file contents type 1."""
        self.account_currency = self.data.row(1)[6].value
        self.header = [c.value.lower() for c in self.data.row(0)]
        self.account_number = '123456789' #Stripe account number in Odoo
        self.name = 'Stripe'

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account = self.account_number
        self.current_statement.statement_id = 'Stripe %s - %s' % (self.data.row(1)[3].value,
                                                           self.data.row(self.data.nrows-1)[3].value) 
        self.current_statement.start_balance = 0.0
        for t in StripeIterator(self.data, header_row=0):
            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = float(t['amount'])
            transaction.original_amount = float(t['amount'])
            self.current_statement.end_balance += float(t['amount'])
            transaction.eref = t['description']
            transaction.name = '%s,%s' % (t['customer email'], t['description'].strip())
            transaction.value_date = t[u'created (utc)']
            #transaction.unique_import_id =
            #transaction.email = t['customer email']

        self.statements.append(self.current_statement)
        return self


class StripeIterator(object):
    def __init__(self, data,header_row=0):
        self.row = header_row + 1
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
