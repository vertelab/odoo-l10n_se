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
from io import BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.addons.l10n_se_account_bank_statement_import.account_bank_statement_import import BankStatement

import logging
_logger = logging.getLogger(__name__)

from openpyxl import load_workbook
from xlrd import open_workbook, XLRDError
from xlrd.book import Book
from xlrd.sheet import Sheet

import sys


class IzettleTransaktionsrapportXlsType(object):
    """Parser for iZettle Kontohändelser import files."""

    def __init__(self, data_file):
        try:
            #~ self.data_file = open_workbook(file_contents=data_file)
            self.data = open_workbook(file_contents=data_file).sheet_by_index(0)
        except XLRDError as e:
            _logger.error(u'Could not read file (iZettle Kontohändelser.xlsx)')
            raise ValueError(e)
        if not (self.data.cell(5,0).value[:20] == u'Betalningsmottagare:' and self.data.cell(10,0).value[:21] == u'Betalningsförmedlare:'):
            _logger.error(u'Row 0 %s (was looking for Betalningsmottagare) %s %s' % (self.data.cell(5,0).value[:20], self.data.cell(10,0).value[:21], self.data.cell(3,2)))
            raise ValueError(u'This is not a iZettle Report')

        self.nrows = self.data.nrows - 17
        self.header = []
        self.statements = []

    def parse(self):
        """Parse iZettle transaktionsrapport bank statement file type 1."""

        self.account_currency = 'SEK'
        self.header = [c.value.lower() for c in self.data.row(16)]
        self.account_number = self.data.cell(13,2).value
        self.name = self.data.cell(5,2).value

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number
        self.current_statement.statement_id = 'iZettle %s' % self.data.cell(3,2).value
        self.current_statement.start_balance = 0.0
        for t in IzettleIterator(self.data, header_row=16):
            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = float(t['netto'])
            transaction.original_amount = float(t['totalt'])
            self.current_statement.end_balance += float(t['netto'])
            transaction.eref = int(t['kvittonummer'])
            transaction.name = '%s %s' % (t['korttyp'].strip(),t['sista siffror'].strip())
            transaction.note = 'Totalt: %s\nMoms: %s\nAvgift: %s\n%s %s' % (float(t['totalt']), t['moms (25.0%)'], t['avgift'], t['korttyp'].strip(), t['sista siffror'].strip())
            transaction.value_date = t[u'datum']
            transaction.unique_import_id = int(t['kvittonummer'])

        self.statements.append(self.current_statement)
        return self

class IzettleTranskationReportXlsxType(object):
    """ Parser for iZettle Kontohändelser import files. """
    def __init__(self, data_file):
        try:
            wb = load_workbook(filename=BytesIO(data_file))
            ws = wb.get_sheet_names()
            _logger.debug(ws) #REQURIED? DELETE AT YOUR OWN RISK. 
            self.data = wb.get_sheet_by_name(ws[0])
        # TODO?: Catch BadZipFile, IOerror, ValueError
        except:
            raise ValueError('This is not a iZettle xlsx document')
        if not (self.data.cell(6,3).value == u'Personal' and self.data.cell(6,13).value == u'Streckkod'):
            _logger.error(u'Header should contain "Personal" and "Streckkod" columns but found "{}" and "{}" instead.'.format(self.data.cell(6,3).value, self.data.cell(6,13).value))
            raise ValueError(u'This is not a iZettle xlsx Report')
        
        self.header = []
        self.statements = []
        
    def parse(self):
        """ Parse iZettle transactionsreport bank statement file type 2. """
        
        self.account_currency = 'SEK'
        self.account_number = "556806-0734" #TODO: Change to actual sheet value? There is none currently?
        self.name = self.data.cell(4,3).value

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number
        self.current_statement.statement_id = 'iZettle %s' % self.data.cell(4,3).value
        self.current_statement.start_balance = 0.0
        self.current_statement.end_balance = 0.0
        
        for index, row in enumerate(self.data.iter_rows(6, values_only=True), start=6):
            if (index == 6):
                self.header = {c:i for i, c in enumerate(row)}
            else:
                transaction_dict = {key:row[self.header[key]] for key in self.header}
                transaction = self.current_statement.create_transaction()
                transaction['amount'] = transaction_dict['Slutpris (SEK)']
                transaction['account_number'] = self.account_number
                transaction['original_amount'] = transaction_dict[u'Slutpris (SEK)']
                transaction['date'] = transaction_dict['Tid'].strftime("%Y-%m-%d")
                transaction['name'] = transaction_dict['Namn'].strip()
                self.current_statement.end_balance += transaction_dict[u'Slutpris (SEK)']
                
        _logger.info(self.current_statement)
        self.statements.append(self.current_statement)
        return self

class IzettleIterator(object):
    def __init__(self, data,header_row=16):
        self.row = header_row + 1
        self.data = data
        self.header = [c.value.lower() for c in data.row(header_row)]

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.data.nrows - 3:
            raise StopIteration
        r = self.data.row(self.row)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
