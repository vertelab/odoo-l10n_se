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
import io
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.addons.l10n_se_account_bank_statement_import.account_bank_statement_import import BankStatement

import logging
_logger = logging.getLogger(__name__)

from xlrd import open_workbook, XLRDError
from xlrd.book import Book
from xlrd.sheet import Sheet

import sys
import csv
import tempfile


class PaypalTransaktionsrapportType(object):
    """Parser for PayPal Kontohändelser import files."""

    def __init__(self, data_file):
        try:
            file = io.StringIO(data_file.decode("utf-8"))
            file.seek(0)
            rows = []
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                rows.append(row)
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read CSV file')
            raise ValueError(e)
        if 'To Email Address' not in self.data[0].keys() or 'Transaction ID' not in self.data[0].keys() or 'Invoice Number' not in self.data[0].keys():
            _logger.error(u'Row 0 was looking for "To Email Address", "Transaction ID" and "Invoice Number".')
            raise ValueError(u'This is not a PayPal Report')

        self.nrows = len(self.data)
        self.header = []
        self.statements = []

    def parse(self):
        """Parse PayPal transaktionsrapport bank statement file contents."""
        self.header = self.data[0].keys()
        self.account_currency = 'SEK'
        self.account_number = self.data[0].get('To Email Address')

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number
        self.current_statement.statement_id = 'PayPal %s - %s' % (self.data[0].get('Date'), self.data[-1].get('Date'))
        self.current_statement.start_balance = 0.0
        # ~ for t in PaypalIterator(self.data, self.nrows, self.header, header_row=0):
        for t in self.data:
            if t['Currency'] == 'EUR':
                eur = request.env['res.currency'].search([('name','=', 'EUR')])
                t['Gross'] = round(float(t['Gross'].replace(',', '')) / eur.rate, 2)
                t['Fee'] = round(float(t['Fee'].replace(',', '')) / eur.rate, 2)
                t['Net'] = round(float(t['Net'].replace(',', '')) / eur.rate, 2)
            elif t['Currency'] == 'USD':
                usd = request.env['res.currency'].search([('name','=', 'USD')])
                t['Gross'] = round(float(t['Gross'].replace(',', '')) / usd.rate, 2)
                t['Fee'] = round(float(t['Fee'].replace(',', '')) / usd.rate, 2)
                t['Net'] = round(float(t['Net'].replace(',', '')) / usd.rate, 2)
            else:
                t['Gross'] = float(t['Gross'].replace(',', ''))
                t['Fee'] = float(t['Fee'].replace(',', ''))
                t['Net'] = float(t['Net'].replace(',', ''))
            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = t['Gross']
            self.current_statement.end_balance += t['Gross']
            transaction.eref = (t['Invoice Number'])
            transaction.name = '%s (%s)' % (t['Name'].strip(), t['From Email Address'].strip())
            transaction.note = 'Brutto: %s\nAvgift: %s\nNetto: %s\nTransaction ID: %s' % (t['Gross'], t['Fee'], t['Net'], t['Transaction ID'])
            transaction.value_date = '%s-%s-%s' %(t['Date'][-4:], t['Date'][3:5], t['Date'][0:2])
            transaction.unique_import_id = t['Invoice Number']

        self.statements.append(self.current_statement)
        return self


# ~ class PaypalIterator(object):
    # ~ def __init__(self, data, nrows, header, header_row=1):
        # ~ self.row = header_row + 1
        # ~ self.nrows = nrows
        # ~ self.data = data
        # ~ self.header = header

    # ~ def __iter__(self):
        # ~ return self

    # ~ def next(self):
        # ~ if self.row >= self.nrows - 1:
            # ~ raise StopIteration
        # ~ r = self.data[(self.row)]
        # ~ self.row += 1
        # ~ return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
