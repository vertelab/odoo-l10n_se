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
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning



import logging
_logger = logging.getLogger(__name__)

import csv
import os
import tempfile

class NordeaTransaktionsrapport(object):
    """Parser for Nordea Transaktions import files (CSV)."""

    def __init__(self, data_file):
        _logger.error('Parser %s' % data_file)
        
        try:
            rows = []
            fp = tempfile.TemporaryFile()
            fp.write(data_file)
            fp.seek(0)
            reader = csv.DictReader(fp,delimiter=";")
            for row in reader:
                rows.append(row)
            fp.close()
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read CSV file')
            raise ValueError(e)
        _logger.error('%s' % self.data[0].keys())
        if not self.data[0].keys() == ['Avs\xc3\xa4ndare', 'Mottagare', '\xef\xbb\xbfBokf\xc3\xb6ringsdag', 'Belopp', 'Valuta', 'Namn', 'Saldo', 'Meddelande', 'Typ', 'Rubrik']:
            _logger.error(u'Row 0 was looking for "To Email Address", "Transaction ID" and "Invoice Number".')
            raise ValueError('This is not a Nordbanken Transaktionsrapport')

        self.nrows = len(self.data)
        self.header = []
        self.statements = []


        # ~ self.rows = self.data.nrows - 3
        # ~ _logger.error('Row 2 %s' % self.data.row(1))
        # ~ self.header = [c.value.lower() for c in self.data.row(1)]
        # ~ self.balance_start = float(self.data.cell(2,11).value) - float(self.data.cell(2,10).value)
        # ~ self.balance_end_real = float(self.data.cell(self.data.nrows - 1,11).value)
        # ~ self.balance_end = 0.0


    def parse(self):
        """Parse Nordea bank statement file contents."""
        return NordeaIterator(self.data,len(self.data),['Avs\xc3\xa4ndare', 'Mottagare', '\xef\xbb\xbfBokf\xc3\xb6ringsdag', 'Belopp', 'Valuta', 'Namn', 'Saldo', 'Meddelande', 'Typ', 'Rubrik'])
       
       

class NordeaIterator(object):

    def __init__(self, data, nrows, header, header_row=1):
        # ~ self.row = header_row + 1
        self.nrows = nrows
        # ~ self.data = data
        # ~ self.header = header
        self.row = 0
        self.data = data
        self.rows = nrows - 2
        self.header = header
        # ~ self.account = account()
        # ~ self.account.routing_number = self.data.row(2)[2].value
        # ~ self.account.balance_start = self.data.row(2)[11].value
        # ~ self.account.balance_end = self.data.row(data.nrows-1)[11].value
        # ~ self.account.currency = self.data.row(2)[4].value
        # ~ self.account.number = self.data.row(2)[1].value + self.data.row(2)[2].value
        # ~ self.account.name = self.data.cell(0,0).value



    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.nrows - 1:
            raise StopIteration
        r = self.data[(self.row)]
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: