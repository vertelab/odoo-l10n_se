# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GMaxNU Affero General Public License as published
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

from xlrd import open_workbook
from xlrd.book import Book
from xlrd.sheet import Sheet

class SwedbankTransaktionsrapport(object):
    """Parser for Swedbank Transaktionsrapport import files."""
    
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 3
        self.header = [c.value.lower() for c in data.row(2)]
        self.balance_start = 0.0
        self.balance_end_real = 0.0
        self.balance_end = 0.0
        

    def parse(self, data):
        """Parse swedbank transaktionsrapport bank statement file contents."""
        if not self.data.cell(0,0).value[:21] == '* Transaktionsrapport':
            raise ValueError('This is not a Swedbank Transaktionsrapport')
            
        self.balance_start = float(self.data.cell(3,11).value)
        self.balance_end_real = float(self.data.cell(self.rows,11).value)
        
        header = {
            'valutadag': 'date',
            'referens': 'payee',
            'text': 'memo',
            'belopp': 'amount',
            }
             
        return {header.get(n,n): t[n] for n in t.keys() for t in SwedbankIterator(data)}
        

class SwedbankIterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = data.nrows - 3
        self.header = [c.value.lower() for c in data.row(1)]
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data.row(self.row + 3)
        self.row += 1
        return {self.header[n]: r[n].value for n in range(len(self.header))}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
