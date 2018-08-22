# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel AB <http://vertel.se>
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
try:
    from xlrd import open_workbook, XLRDError
    from xlrd.book import Book
    from xlrd.sheet import Sheet
except:
    _logger.info('xlrd not installed.')

class SwedbankTransaktionsrapport(object):
    """Parser for Swedbank Transaktionsrapport import files."""
    
    def __init__(self, data_file):
        self.row = 0
        try:
            self.data = open_workbook(file_contents=data_file).sheet_by_name('Transaktionsrapport')
        except XLRDError, e:
            raise ValueError(e)                
        self.rows = self.data.nrows - 3
        _logger.error('Row 2 %s' % self.data.row(1))
        self.header = [c.value.lower() for c in self.data.row(1)]
        self.balance_start = float(self.data.cell(2,11).value) - float(self.data.cell(2,10).value)
        self.balance_end_real = float(self.data.cell(self.data.nrows - 1,11).value)
        self.balance_end = 0.0

    def parse(self):
        """Parse swedbank transaktionsrapport bank statement file contents."""
        if not self.data.cell(0,0).value[:21] == '* Transaktionsrapport':
            raise ValueError('This is not a Swedbank Transaktionsrapport')
        
        header = {
            'valutadag': 'date',
            'referens': 'payee',
            'text': 'memo',
            'belopp': 'amount',
            }
             
        #_logger.error('t: %s' % [t.keys() for t in SwedbankIterator(self.data)])
        #raise Warning([n for n in [t.keys() for t in SwedbankIterator(self.data)]])
        #return {header.get(n,n): t[n] for n in [t.keys() for t in SwedbankIterator(self.data)]}
        return SwedbankIterator(self.data)
        
        
class account(object):
    pass

class SwedbankIterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 2
        self.header = [c.value.lower() for c in data.row(1)]
        self.account = account()
        self.account.routing_number = self.data.row(2)[2].value
        self.account.balance_start = self.data.row(2)[11].value
        self.account.balance_end = self.data.row(data.nrows-1)[11].value
        self.account.currency = self.data.row(2)[4].value
        self.account.number = self.data.row(2)[1].value + self.data.row(2)[2].value
        self.account.name = self.data.cell(0,0).value

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 2)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}


class SwedbankSwish(object):
    """Parser for Swedbank Swish import files."""
    
    def __init__(self, data_file):
        self.row = 0
        self.data = open_workbook(file_contents=data_file).sheet_by_name('Swish-rapport')
        self.rows = self.data.nrows - 3
        _logger.error('Row 2 %s' % self.data.row(1))
        self.header = [c.value.lower() for c in self.data.row(1)]
        self.balance_start = 0.0
        self.balance_end_real = 0.0
        self.balance_end = 0.0
        

    def parse(self):
        """Parse swedbank transaktionsrapport bank statement file contents."""
        if not self.data.cell(0,0).value[:15] == '* Swish-rapport':
            raise ValueError('This is not a Swedbank Swish-rapport')
            
        self.balance_start = float(self.data.cell(3,11).value)
        self.balance_end_real = float(self.data.cell(self.rows,11).value)
        
        header = {
            'valutadag': 'date',
            'referens': 'payee',
            'text': 'memo',
            'belopp': 'amount',
            }
             
        #_logger.error('t: %s' % [t.keys() for t in SwedbankIterator(self.data)])
        #raise Warning([n for n in [t.keys() for t in SwedbankIterator(self.data)]])
        #return {header.get(n,n): t[n] for n in [t.keys() for t in SwedbankIterator(self.data)]}
        return SwedbankIterator(self.data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
