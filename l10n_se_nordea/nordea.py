# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2020 Vertel AB <http://vertel.se>
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
import io
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning



import logging
_logger = logging.getLogger(__name__)

from csv import DictReader
import os
import tempfile

class NordeaTransaktionsrapport(object):
    """Parser for Nordea Transaktions import files (CSV)."""

    def __init__(self, data_file):
        # _logger.error('Parser %s' % data_file)
        try:
            rows = []
            fp = io.StringIO(data_file.decode("utf-8"))
            fp.seek(0)
            reader = DictReader(fp, delimiter=";")
            for row in reader:
                rows.append(row)
            fp.close()
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read CSV file')
            raise ValueError(e)
        # _logger.error('%s' % self.data[0].keys())
        if not ('\ufeffBokföringsdag' in self.data[0] and 'Belopp' in self.data[0] and 'Saldo' in self.data[0]):
            _logger.error(u'Row 0 was looking for "To Email Address", "Transaction ID" and "Invoice Number".')
            raise ValueError('This is not a Nordbanken Transaktionsrapport')

        self.nrows = len(self.data)
        self.header = []
        self.statements = []


        

    def parse(self):
        """Parse Nordea bank statement file contents."""
        print(self.data)
        return NordeaIterator(self.data,len(self.data),['\ufeffBokföringsdag', 'Belopp', 'Avsändare', 'Mottagare', 'Namn', 'Rubrik', 'Meddelande', 'Saldo', 'Valuta', 'Typ'])
       
class account(object):
    pass

class NordeaIterator(object):

    def __init__(self, data, nrows, header, header_row=1):
        self.nrows = nrows
        self.row = 0
        self.data = data
        self.rows = nrows - 2
        self.header = header

        self.balance_start = float(self.data[2]['Belopp'].replace(",","."))
        self.currency = self.data[2]['Valuta']

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.nrows - 1:
            raise StopIteration
        r = self.data[(self.row)]
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

    def __next__(self):
        if self.row >= self.nrows - 1:
            raise StopIteration
        r = self.data[(self.row)]
        self.row += 1
        return {self.header[n]: r[self.header[n]] for n in range(len(self.header))}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
