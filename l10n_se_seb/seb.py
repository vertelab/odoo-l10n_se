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
            self.data = open_workbook(file_contents=data_file,filename="k.xlsx",logfile='/tmp/xlrd.log',verbosity=1).sheet_by_index(0)
        except XLRDError, e:
            _logger.error(u'Could not read file (SEB Kontohändelser.xlsx)')
            raise ValueError(e)  
        self.rows = self.data.nrows - 3
        self.header = [c.value.lower() for c in self.data.row(1)]
        self.balance_start = 0.0
        self.balance_end_real = 0.0
        self.balance_end = 0.0
        

    def parse(self):
        """Parse swedbank transaktionsrapport bank statement file contents."""
        if not (self.data.cell(0,0).value[:14] == u'Företagsnamn:' and self.data.cell(0,3).value[:12] == u'Sökbegrepp:'):
            _logger.error(u'Row 0 %s (was looking for Företagsnamn)' % self.data.row(0))
            raise ValueError('This is not a SEB Transaktionsrapport')
            
        self.balance_start = float(self.data.cell(self.rows,5).value - self.data.cell(self.rows,4).value)
        self.balance_end_real = float(self.data.cell(6,1).value)
        
             
        #_logger.error('t: %s' % [t.keys() for t in SwedbankIterator(self.data)])
        #raise Warning([n for n in [t.keys() for t in SwedbankIterator(self.data)]])
        #return {header.get(n,n): t[n] for n in [t.keys() for t in SwedbankIterator(self.data)]}
        return SEBIterator(self.data)
        
        
class account(object):
    pass

class SEBIterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 3
        self.header = [c.value.lower() for c in data.row(1)]
        self.account = account()
#        self.account.routing_number = self.data.row(3)[2].value
        self.account.balance_start = float(self.data.cell(self.rows,5).value - self.data.cell(self.rows,4).value)
        self.account.balance_end = float(self.data.cell(6,1).value)
        self.account.currency = 'SEK'
        self.account.number = self.data.cell(6,0).value
        self.account.name = self.data.cell(0,0).value[15:30]
        
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 3)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
